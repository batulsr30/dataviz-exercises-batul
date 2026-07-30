# pages/03_demand.py — demand story (BBD squiggle: summary → area → demand)
# Demand proxy: reviews_per_month (Inside Airbnb's standard occupancy signal).
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils import load_data, sidebar_filters

df, p95 = load_data()
filtered = sidebar_filters(df, p95)  # SAME shared sidebar — filters persist onto this page

st.title('Where is guest demand strongest?')
st.caption('BBD squiggle: market summary → neighbourhood story → where guests actually book')

# ── Own persisted widget: focus room type ────────────────────────────────────
# Same keep-alive trick as the filters, plus a guard in case the current filters
# removed the previously-selected room type.
if 'sel_room' not in st.session_state:
    st.session_state.sel_room = sorted(filtered['room_type'].unique())[0]
st.session_state.sel_room = st.session_state.sel_room     # keep alive across pages

rooms_avail = sorted(filtered['room_type'].unique())
if st.session_state.sel_room not in rooms_avail:          # guard: filters may have
    st.session_state.sel_room = rooms_avail[0]            # removed the saved choice

st.selectbox('Focus on a room type', rooms_avail, key='sel_room')
room = st.session_state.sel_room

# ── KPI row — passes the 5-second test ───────────────────────────────────────
demand_by_hood = (filtered.groupby('neighbourhood')['reviews_per_month']
                  .mean().sort_values(ascending=False))
busiest_hood = demand_by_hood.index[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric('Total Reviews/Month', f"{filtered['reviews_per_month'].sum():,.0f}",
          help='Sum of monthly reviews — total booking activity')
k2.metric('Median Reviews/Listing', f"{filtered['reviews_per_month'].median():.1f}")
k3.metric('Busiest Area', busiest_hood,
          f"{demand_by_hood.iloc[0]:.1f} reviews/mo")
k4.metric(f'{room} — Median Demand',
          f"{filtered.loc[filtered['room_type'] == room, 'reviews_per_month'].median():.1f}",
          'reviews/mo')

st.divider()

col_left, col_right = st.columns([1.5, 1])

with col_left:
    # Insight title = the finding, not the topic
    st.subheader(f'{busiest_hood} sees the most guest activity')
    top = demand_by_hood.head(12).reset_index()
    top.columns = ['neighbourhood', 'reviews_per_month']

    # highlight column → declarative colour mapping (no per-trace loop)
    # BBD HIGHLIGHT: blue for the busiest area, grey recedes
    # BBD CVD: blue vs grey — no red-green combination
    top['highlight'] = top['neighbourhood'].apply(
        lambda n: 'Busiest' if n == busiest_hood else 'Other')
    fig1 = px.bar(top, x='reviews_per_month', y='neighbourhood', orientation='h',
                  color='highlight',
                  color_discrete_map={'Busiest': '#2E75B6', 'Other': '#AAAAAA'},
                  category_orders={'neighbourhood': top['neighbourhood'].tolist()[::-1]},
                  labels={'reviews_per_month': 'Avg Reviews / Month', 'neighbourhood': ''})
    fig1.update_traces(marker_line_width=0)
    fig1.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                       showlegend=False, font=dict(family='Arial', size=11),
                       xaxis=dict(gridcolor='#EEEEEE'), yaxis=dict(showgrid=False),
                       margin=dict(l=10, r=10, t=5, b=10))
    st.plotly_chart(fig1, use_container_width=True)

with col_right:
    st.subheader(f'How demand for {room} compares')
    # highlight the chosen room type against the rest of the market
    # BBD HIGHLIGHT: blue for the focus room type, grey for the rest
    # BBD CVD: blue vs grey — no red-green combination
    # histnorm='percent' so a small segment is comparable to the whole market
    plot_df = filtered.copy()
    plot_df['highlight'] = plot_df['room_type'].apply(
        lambda r: room if r == room else 'Rest of market')
    fig2 = px.histogram(plot_df, x='reviews_per_month', color='highlight',
                        barmode='overlay', histnorm='percent', nbins=40,
                        color_discrete_map={room: '#2E75B6', 'Rest of market': '#AAAAAA'},
                        labels={'reviews_per_month': 'Reviews / Month', 'highlight': ''})
    fig2.update_traces(marker_line_width=0)
    fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                       font=dict(family='Arial', size=11),
                       yaxis=dict(gridcolor='#EEEEEE', title='% of listings'),
                       xaxis=dict(showgrid=False),
                       legend=dict(orientation='h', y=1.12),
                       margin=dict(l=10, r=10, t=5, b=10))
    st.plotly_chart(fig2, use_container_width=True)

with st.expander('📊 Demand ranking (all filtered neighbourhoods)'):
    st.dataframe(demand_by_hood.round(2).reset_index()
                 .rename(columns={'reviews_per_month': 'avg_reviews_per_month'}),
                 use_container_width=True)

st.divider()
st.caption(
    f'Inside Airbnb (insideairbnb.com) | Demand proxied by reviews/month | '
    f'Prices capped at 95th percentile (£{p95:.0f}) | Last shown: {datetime.date.today()}'
)

# PERSISTENCE TEST: set filters on page 1, pick a room type here, switch to
# page 2 and back — filters AND the room-type selection are where you left them.
