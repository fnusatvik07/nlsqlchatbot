import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import create_engine, text
import matplotlib.pyplot as plt
import io
import base64

# SQLite connection details
sqlite_db_file = '/Users/fnusatvik/text2query/cookies.db'  # SQLite database file
sqlite_engine = create_engine(f'sqlite:///{sqlite_db_file}')

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Custom color palette for charts
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

# Function to convert NL to SQL using OpenAI's GPT-4
def convert_to_sql(question):
    # Using a dummy SQL query for illustration
    # Replace this with the call to GPT-4 to get the actual query
    if "classification" in question.lower():
        sql_query = "SELECT classification, COUNT(*) as count FROM cookies GROUP BY classification;"
    elif "vendor" in question.lower():
        sql_query = "SELECT vendor, COUNT(*) as count FROM cookies GROUP BY vendor;"
    else:
        sql_query = "SELECT classification, COUNT(*) as count FROM cookies GROUP BY classification;"
    
    return sql_query

# Function to execute SQL query
def execute_sql_query(query):
    rows = []
    columns = []
    try:
        with sqlite_engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
            columns = list(result.keys())
    except Exception as e:
        print(f"Error executing SQL query: {e}")
    return rows, columns

# Function to generate and display chart and insights
def generate_chart_and_insights(data, columns):
    df = pd.DataFrame(data, columns=columns)
    
    if 'classification' in df.columns:
        group_by_column = 'classification'
    elif 'vendor' in df.columns:
        group_by_column = 'vendor'
    else:
        group_by_column = columns[0]
    
    count_column = 'count'
    if count_column not in df.columns:
        count_column = df.columns[-1]  # Assume the last column is the count column if not named 'count'
    
    # Generate chart as a base64 string
    fig, ax = plt.subplots(figsize=(6, 6))
    
    if group_by_column == 'classification':
        # Generate a pie chart
        df.set_index(group_by_column)[count_column].plot(kind='pie', ax=ax, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.set_ylabel('')  # Hide the y-label for pie chart
    else:
        # Generate a bar chart
        df.set_index(group_by_column)[count_column].plot(kind='bar', ax=ax, color=colors, edgecolor='black')
        ax.set_ylabel('Count')
    
    ax.set_title(f"Distribution by {group_by_column.capitalize()}")
    plt.grid(visible=False)
    chart_img = io.BytesIO()
    plt.savefig(chart_img, format='png', bbox_inches='tight')
    chart_img.seek(0)
    chart_base64 = base64.b64encode(chart_img.read()).decode('utf-8')
    plt.close()

    # Generate insights
    total_count = df[count_column].sum()
    max_category = df.loc[df[count_column].idxmax(), group_by_column]
    max_value = df[count_column].max()
    min_category = df.loc[df[count_column].idxmin(), group_by_column]
    min_value = df[count_column].min()

    insights = [
        f"Total number of cookies: {total_count}",
        f"The category with the highest count is '{max_category}' with {max_value} cookies.",
        f"The category with the lowest count is '{min_category}' with {min_value} cookies."
    ]

    return chart_base64, insights, df

# Layout of the app
app.layout = dbc.Container(
    [
        dbc.Row(dbc.Col(html.H1("SQL Generative Business Intelligence Report", className="text-center text-primary mb-4"), width=12)),
        
        dbc.Row(
            [
                dbc.Col(
                    dbc.Input(id="user_question", placeholder="Type your natural language question here...", type="text"),
                    width=8
                ),
                dbc.Col(
                    dbc.Button("Generate Report", id="submit_button", color="primary", className="mt-1"),
                    width=2
                ),
            ],
            justify="center"
        ),
        
        dbc.Row(
            [
                dbc.Col(
                    html.Div(id="output_chart"),
                    width=6
                ),
                dbc.Col(
                    [
                        html.H3("Top 3 Insights", className="text-center text-info mb-3"),
                        html.Ul(id="output_insights")
                    ],
                    width=6
                ),
            ],
            className="mt-4"
        ),
        
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4("Final Output Table", className="text-center text-secondary mt-4"),
                        html.Div(id="output_table")
                    ],
                    width=12
                ),
            ],
            className="mt-4"
        ),
        
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H5("Navigation Tips", className="text-center text-muted mt-5"),
                        html.P("Use the input box above to type your question in natural language. You can ask for distributions across classifications or vendors. The generated chart will appear on the left, and insights will be displayed on the right.", className="text-center"),
                        html.P("Scroll down to view the final output table, which shows the raw data used to generate the chart. The chart colors are carefully chosen for clarity and aesthetics.", className="text-center")
                    ],
                    width=12
                ),
            ],
            className="mt-4"
        )
    ],
    fluid=True
)

# Callback to update chart, insights, and table based on user input
@app.callback(
    [Output("output_chart", "children"), Output("output_insights", "children"), Output("output_table", "children")],
    [Input("submit_button", "n_clicks")],
    [State("user_question", "value")]
)
def update_output(n_clicks, user_question):
    if n_clicks is None or not user_question:
        return "", "", ""
    
    # Generate SQL query
    sql_query = convert_to_sql(user_question)
    
    # Execute SQL query
    data, columns = execute_sql_query(sql_query)
    
    # Generate chart, insights, and get the final output table
    chart_base64, insights, df = generate_chart_and_insights(data, columns)
    
    # Create table for the final output
    table = dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, dark=False)
    
    # Return the chart, insights, and table
    return html.Img(src=f'data:image/png;base64,{chart_base64}', style={"width": "100%"}), [html.Li(insight) for insight in insights], table

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, port=8972)
