
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="CO2 Dashboard", page_icon="🌱", layout="wide")

# Palette: one accent + one grey is the whole SWD colour system.
ACCENT = "#1B6CA8"
GREY = "#C9CCD1"

# ── Data ──────────────────────────────────────────────────────────────────────
# @st.cache_data: Streamlit reruns the entire script on every widget interaction.
# Without caching, the CSV is read from disk on every interaction — slow and wasteful.
# cache_data stores the result after the first run and reuses it until the file changes.
@st.cache_data
def load_data():
    path = Path(__file__).parent.parent / 'data' / 'co2_emissions.csv'
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-01-01')
    return df

df = load_data()

st.title("🌱 CO2 Emissions Explorer")
st.caption("Source: Our World in Data — ourworldindata.org/co2-emissions")

# ── TASK 1: Sidebar with 5 widgets ────────────────────────────────────────────
#   a) st.selectbox for Region (with 'All')
#   b) st.multiselect for Countries (updates based on region — chained)
#   c) st.date_input for date range (two-handle; convert years to Jan-1 dates)
#   d) st.radio for Metric: "Total CO2 (Mt)" vs "CO2 per capita"
#   e) st.checkbox labelled "Show only top emitter highlighted"
#
# Guards:
#   - empty countries → st.warning + st.stop()
#   - incomplete date_input → st.warning + st.stop()
# Convert date_input result to pd.Timestamp before filtering.
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # (a) Region — 'All' first so the default is the most common case (BBD rule)
    regions = ['All'] + sorted(df['Region'].unique().tolist())
    selected_region = st.selectbox("Region", regions)

    # Narrow the pool BEFORE building the next widget — this is the chaining step
    region_df = df if selected_region == 'All' else df[df['Region'] == selected_region]

    # (b) Countries — options come from the region chosen above, not the whole df
    country_options = sorted(region_df['Country'].unique().tolist())
    default_countries = (
        region_df.groupby('Country')['CO2_Mt'].sum().nlargest(4).index.tolist()
    )
    selected_countries = st.multiselect(
        "Countries", country_options, default=default_countries
    )

    # (c) Date range — tuple as `value` gives the two-handle version.
    # Data is annual, so every date is Jan 1 (converted in load_data).
    min_date = df['Date'].min().date()
    max_date = df['Date'].max().date()
    date_range = st.date_input(
        "Date range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date
    )

    # (d) Metric
    metric = st.radio("Metric", ["Total CO2 (Mt)", "CO2 per capita"])

    # (e) Highlight toggle
    highlight_top = st.checkbox("Show only top emitter highlighted")

# Map the radio label onto the actual column name
METRIC_COL = {"Total CO2 (Mt)": "CO2_Mt", "CO2 per capita": "CO2_per_capita"}
metric_col = METRIC_COL[metric]
metric_unit = "Mt CO₂" if metric_col == "CO2_Mt" else "t CO₂ / person"

# Guards — st.stop() halts cleanly. Without it the code below crashes on an empty
# selection and the user sees a red traceback instead of a helpful message.
if not selected_countries:
    st.warning("👆 Select at least one country in the sidebar.")
    st.stop()

# While the user is mid-click on the calendar, date_input returns a 1-tuple
if len(date_range) != 2:
    st.warning("👆 Pick both a start and an end date to continue.")
    st.stop()

# date_input returns datetime.date; the dataframe holds Timestamps
start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
if start > end:
    st.warning("Start date is after end date — swap them to continue.")
    st.stop()

filtered = region_df[
    region_df['Country'].isin(selected_countries)
    & region_df['Date'].between(start, end)
].copy()

if filtered.empty:
    st.warning("No records match these filters. Try widening the date range.")
    st.stop()

# ── TASK 2: Filter summary caption ────────────────────────────────────────────
# Show: "X countries | Region | Date range | Metric"
# BBD rule: always show users how many records match current filters
# ─────────────────────────────────────────────────────────────────────────────
first_year, last_year = int(filtered['Year'].min()), int(filtered['Year'].max())

st.caption(
    f"Showing **{filtered['Country'].nunique()} of {df['Country'].nunique()} countries** "
    f"| Region: **{selected_region}** "
    f"| **{first_year}–{last_year}** "
    f"| Metric: **{metric}** "
    f"| {len(filtered):,} records"
)

# ── EXTENSION: KPI row above the charts ───────────────────────────────────────
#   - Total CO2 in last year of selected range (sum across selected countries)
#   - % change from first to last year
#   - Country with highest emissions in last year
# ─────────────────────────────────────────────────────────────────────────────
# Totals sum across countries; per-capita rates must be averaged — adding
# per-person rates together is meaningless.
agg = 'sum' if metric_col == 'CO2_Mt' else 'mean'

last_slice = filtered[filtered['Year'] == last_year]
first_slice = filtered[filtered['Year'] == first_year]

last_value = getattr(last_slice[metric_col], agg)()
first_value = getattr(first_slice[metric_col], agg)()
pct_change = (last_value - first_value) / first_value * 100 if first_value else 0.0

top_row = last_slice.loc[last_slice[metric_col].idxmax()]

col1, col2, col3 = st.columns(3)
col1.metric(
    f"{'Total' if agg == 'sum' else 'Average'} in {last_year}",
    f"{last_value:,.1f} {metric_unit}"
)
col2.metric(
    f"Change since {first_year}",
    f"{pct_change:+.1f}%",
    delta=f"{last_value - first_value:+,.1f} {metric_unit}",
    delta_color="inverse"   # rising emissions is bad news — red, not green
)
col3.metric(f"Highest in {last_year}", top_row['Country'],
            delta=f"{top_row[metric_col]:,.1f} {metric_unit}", delta_color="off")

st.divider()

# ── TASK 3: Two charts reacting to ALL filters ────────────────────────────────
#   Left: line chart — selected metric over time, one line per country
#         If "Show only top emitter highlighted" checkbox is on:
#           - grey all lines except the highest emitter in the date range
#           - label that country at the end of its line (SWD grey-and-highlight)
#   Right: bar chart — ranking for the last year in selected date range
#
# BBD colour requirement: name the colour type in a comment next to each chart
# SWD requirements: white background, insight title, use_container_width=True
# ─────────────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

# Who leads across the whole selected range?
range_ranking = getattr(
    filtered.groupby('Country')[metric_col], agg
)().sort_values(ascending=False)
top_country = range_ranking.index[0]

with col_left:
    # Line chart
    if highlight_top:
        # COLOUR TYPE: highlight (grey-out) — one accent hue carries the meaning,
        # every other series drops to neutral grey. Use when one series is the story.
        colour_map = {c: GREY for c in selected_countries}
        colour_map[top_country] = ACCENT
        # Draw the highlighted line last so it sits on top of the grey ones
        draw_order = [c for c in selected_countries if c != top_country] + [top_country]

        fig1 = px.line(filtered, x='Date', y=metric_col, color='Country',
                       color_discrete_map=colour_map,
                       category_orders={'Country': draw_order})
        fig1.for_each_trace(
            lambda t: t.update(line_width=3.5 if t.name == top_country else 1.5)
        )
        fig1.update_layout(showlegend=False)   # the direct label replaces the legend

        # Label the highlighted country at the end of its line — SWD: label directly
        # so the eye never travels to a legend and back
        end_point = filtered[filtered['Country'] == top_country].sort_values('Date').iloc[-1]
        fig1.add_annotation(x=end_point['Date'], y=end_point[metric_col],
                            text=f"  {top_country}", showarrow=False,
                            xanchor='left', font=dict(color=ACCENT, size=13))

        line_title = f"{top_country} leads on {metric.lower()}, {first_year}–{last_year}"
    else:
        # COLOUR TYPE: categorical (qualitative) — countries are unordered labels,
        # so each gets a distinct hue with no implied ranking between them.
        fig1 = px.line(filtered, x='Date', y=metric_col, color='Country',
                       color_discrete_sequence=px.colors.qualitative.Safe)
        fig1.update_traces(line_width=2)
        direction = "rose" if pct_change > 0 else "fell"
        line_title = (f"{metric} {direction} {abs(pct_change):.0f}% across "
                      f"the selection, {first_year}–{last_year}")

    fig1.update_layout(
        title=dict(text=line_title, font=dict(size=17), x=0, xanchor='left'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Arial', size=12),
        margin=dict(l=10, r=110, t=60, b=10),
        xaxis_title=None, yaxis_title=metric_unit,
        hovermode='x unified',
        legend=dict(title=None, orientation='h', y=-0.15)
    )
    fig1.update_xaxes(showgrid=False, showline=True, linecolor=GREY)
    fig1.update_yaxes(showgrid=True, gridcolor='#EEEEEE', zeroline=False)

    st.plotly_chart(fig1, use_container_width=True)

with col_right:
    # Bar chart
    # COLOUR TYPE: sequential — one ordered measure, light-to-dark tracks magnitude.
    ranking = getattr(
        last_slice.groupby('Country')[metric_col], agg
    )().sort_values().reset_index()

    fig2 = px.bar(ranking, x=metric_col, y='Country', orientation='h',
                  color=metric_col, color_continuous_scale='Blues',
                  text=ranking[metric_col].map(lambda v: f"{v:,.0f}"))
    fig2.update_traces(textposition='outside', cliponaxis=False, marker_line_width=0)
    fig2.update_layout(
        title=dict(text=f"{ranking.iloc[-1]['Country']} tops the ranking in {last_year}",
                   font=dict(size=17), x=0, xanchor='left'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Arial', size=12),
        coloraxis_showscale=False,   # bar length already encodes magnitude
        margin=dict(l=10, r=40, t=60, b=10),
        xaxis_title=metric_unit, yaxis_title=None
    )
    fig2.update_xaxes(showgrid=False, showticklabels=False)
    fig2.update_yaxes(showgrid=False)

    st.plotly_chart(fig2, use_container_width=True)
