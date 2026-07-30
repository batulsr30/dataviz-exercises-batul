#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 18 18:50:24 2026

@author: dina.deifallah
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path



# @st.cache_data: Streamlit reruns the entire script on every widget interaction.
# Without caching, the CSV is read from disk on every interaction — slow and wasteful.
# cache_data stores the result after the first run and reuses it until the file changes

@st.cache_data
def load_data():
    path = Path(__file__).parent.parent / 'data' / 'co2_emissions.csv'
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-01-01')
    return df

df = load_data()

st.title("CO₂ Emissions Explorer")

with st.sidebar:
    st.header("Filters")
    
    # filter 1: Multi-select country
    selected_countries = st.multiselect(
        "Countries", sorted(df['Country'].unique()),
        default=['China', 'United States', 'India', 'Germany']
    )
    
    # guard against empty country selection
    if not selected_countries:
        st.warning("Select at least one country.")
        st.stop()
          
    
    # filter 2: slider for year range - use when year is cast as an integer
    # Tuple default → two-handle range slider
    year_range = st.slider("Year range",
        int(df['Year'].min()), int(df['Year'].max()), (2010, 2020))

    # filter 3: which country gets the accent colour (see the fix below)
    highlight_country = st.selectbox("Highlight", sorted(selected_countries))


# applying filtering by country and year range 
filtered = df[
    df['Country'].isin(selected_countries) &
    (df['Year'] >= year_range[0]) &
    (df['Year'] <= year_range[1])
]

# for clarity: showing the number of countries and the number of data points selected
st.caption(f"Showing {len(selected_countries)} countries | {len(filtered)} data points")


# Figure 1: Line chart — BEFORE (the problem)
#
# extended_palette = px.colors.qualitative.Alphabet  # 26 distinct colours
#
# fig = px.line(filtered, x='Year', y='CO2_Mt', color='Country',
#               labels={'CO2_Mt': 'CO2 (Mt)'},
#               color_discrete_sequence=extended_palette)
#
# 26 distinct hues means 26 things competing for attention, so nothing wins.
# Colour stops being information and becomes decoration — the exact failure mode
# BBD warns about. A categorical palette only works while the eye can still hold
# the categories apart, which is roughly 5-7 colours.


### Class exercise: fix the 'too many colors issue here, by using a highlight
### color only for one country and grey the rest'

# THE FIX — grey-and-highlight:
# one accent hue for the country in question, neutral grey for the context.
ACCENT = '#2E75B6'
GREY = '#C9CCD1'

# Every country maps to grey, then the highlighted one is overwritten with the accent
colour_map = {c: GREY for c in selected_countries}
colour_map[highlight_country] = ACCENT

# Plotly draws traces in category order, so listing the highlighted country last
# keeps its line on top of the grey ones instead of buried underneath
draw_order = [c for c in selected_countries if c != highlight_country] + [highlight_country]

fig = px.line(filtered, x='Year', y='CO2_Mt', color='Country',
              labels={'CO2_Mt': 'CO2 (Mt)'},
              color_discrete_map=colour_map,
              category_orders={'Country': draw_order})

# Weight reinforces the colour: thick accent line, thin grey context lines
fig.for_each_trace(
    lambda t: t.update(line_width=3.5 if t.name == highlight_country else 1.5)
)

# Label the highlighted line directly and drop the legend — with only one country
# named, a legend just makes the eye travel back and forth for no reason
end_point = filtered[filtered['Country'] == highlight_country].sort_values('Year').iloc[-1]
fig.add_annotation(x=end_point['Year'], y=end_point['CO2_Mt'],
                   text=f"  {highlight_country}", showarrow=False,
                   xanchor='left', font=dict(color=ACCENT, size=13))

fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                  font=dict(family='Arial'),
                  showlegend=False,
                  margin=dict(r=110))   # room for the end label
st.plotly_chart(fig, use_container_width=True)













