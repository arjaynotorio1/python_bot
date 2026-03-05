import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import logging
from src.database.db_manager import db_manager
from src.mt5.connection import mt5_connection
from src.mt5.gold_data import gold_data_fetcher
from src.config.config import config

logger = logging.getLogger(__name__)


class Dashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.app.title = "Gold Trading Bot Dashboard"
        self.setup_layout()
        self.setup_callbacks()
        
    def setup_layout(self):
        self.app.layout = html.Div([
            html.Div([
                html.H1("🥇 Gold Trading Bot Dashboard", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 
                             'marginBottom': '30px', 'marginTop': '20px'}),
                
                dcc.Interval(
                    id='interval-component',
                    interval=config.DASHBOARD.REFRESH_INTERVAL * 1000,
                    n_intervals=0
                ),
                
                self._create_header_cards(),
                
                html.Div([
                    html.Div([
                        self._create_open_positions_card(),
                        self._create_balance_chart()
                    ], style={'width': '48%', 'display': 'inline-block'}),
                    
                    html.Div([
                        self._create_trades_chart(),
                        self._create_strategy_performance_card()
                    ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
                ], style={'clear': 'both', 'marginTop': '30px'}),
                
                self._create_trade_history_table(),
                self._create_daily_stats_chart()
            ])
        ])
    
    def _create_header_cards(self):
        account_info = mt5_connection.get_account_info()
        balance = account_info['balance'] if account_info else 0
        equity = account_info['equity'] if account_info else 0
        profit = account_info['profit'] if account_info else 0
        
        open_positions = mt5_connection.get_positions()
        open_trades = len(open_positions)
        
        daily_stats = db_manager.get_daily_stats()
        if daily_stats:
            today_stats = daily_stats[0]
            daily_profit = today_stats.get('daily_profit', 0)
            win_rate = today_stats.get('win_rate', 0)
        else:
            daily_profit = 0
            win_rate = 0
        
        return html.Div([
            html.Div([
                html.H3("💰 Balance", style={'fontSize': '16px', 'marginBottom': '10px'}),
                html.H2(f"${balance:,.2f}", style={'fontSize': '24px', 'margin': '0', 
                                                'color': '#27ae60' if balance >= 10000 else '#e74c3c'})
            ], style={'width': '23%', 'display': 'inline-block', 
                     'backgroundColor': '#ecf0f1', 'padding': '20px', 
                     'borderRadius': '10px', 'margin': '1%'}),
            
            html.Div([
                html.H3("📊 Equity", style={'fontSize': '16px', 'marginBottom': '10px'}),
                html.H2(f"${equity:,.2f}", style={'fontSize': '24px', 'margin': '0',
                                                'color': '#27ae60' if equity >= 10000 else '#e74c3c'})
            ], style={'width': '23%', 'display': 'inline-block',
                     'backgroundColor': '#ecf0f1', 'padding': '20px',
                     'borderRadius': '10px', 'margin': '1%'}),
            
            html.Div([
                html.H3("📈 Daily P&L", style={'fontSize': '16px', 'marginBottom': '10px'}),
                html.H2(f"${daily_profit:,.2f}", style={'fontSize': '24px', 'margin': '0',
                                                       'color': '#27ae60' if daily_profit >= 0 else '#e74c3c'})
            ], style={'width': '23%', 'display': 'inline-block',
                     'backgroundColor': '#ecf0f1', 'padding': '20px',
                     'borderRadius': '10px', 'margin': '1%'}),
            
            html.Div([
                html.H3("📊 Win Rate", style={'fontSize': '16px', 'marginBottom': '10px'}),
                html.H2(f"{win_rate:.1%}", style={'fontSize': '24px', 'margin': '0',
                                               'color': '#27ae60' if win_rate >= 0.5 else '#e74c3c'})
            ], style={'width': '23%', 'display': 'inline-block',
                     'backgroundColor': '#ecf0f1', 'padding': '20px',
                     'borderRadius': '10px', 'margin': '1%'})
        ], style={'clear': 'both'})
    
    def _create_open_positions_card(self):
        open_trades = mt5_connection.get_positions()
        
        if not open_trades:
            return html.Div([
                html.H3("📋 Open Positions", style={'marginBottom': '20px'}),
                html.P("No open positions", style={'textAlign': 'center', 'padding': '20px'})
            ], style={'backgroundColor': '#ecf0f1', 'padding': '20px', 
                     'borderRadius': '10px', 'marginBottom': '20px'})
        
        data = []
        for trade in open_trades:
            data.append({
                'Ticket': trade['ticket'],
                'Type': trade['type'],
                'Volume': trade['volume'],
                'Entry': f"${trade['price_open']:.2f}",
                'SL': f"${trade['sl']:.2f}" if trade['sl'] else 'N/A',
                'TP': f"${trade['tp']:.2f}" if trade['tp'] else 'N/A',
                'Profit': f"${trade['profit']:.2f}"
            })
        
        df = pd.DataFrame(data)
        
        return html.Div([
            html.H3("📋 Open Positions", style={'marginBottom': '20px'}),
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([html.Th(col) for col in df.columns])
                    ]),
                    html.Tbody([
                        html.Tr([html.Td(str(df.iloc[i][col])) for col in df.columns])
                        for i in range(len(df))
                    ])
                ])
            ])
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def _create_balance_chart(self):
        return html.Div([
            html.H3("💰 Balance History", style={'marginBottom': '20px'}),
            dcc.Graph(id='balance-chart')
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def _create_trades_chart(self):
        return html.Div([
            html.H3("📊 Trade Results", style={'marginBottom': '20px'}),
            dcc.Graph(id='trades-chart')
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def _create_strategy_performance_card(self):
        strategies = db_manager.get_strategy_performance()
        
        if not strategies:
            return html.Div([
                html.H3("📈 Strategy Performance", style={'marginBottom': '20px'}),
                html.P("No strategy data available", style={'textAlign': 'center', 'padding': '20px'})
            ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                     'borderRadius': '10px', 'marginBottom': '20px'})
        
        data = []
        for strategy in strategies:
            data.append({
                'Strategy': strategy['strategy_name'],
                'Trades': strategy['total_trades'],
                'Win Rate': f"{strategy['win_rate']:.1%}",
                'Total Profit': f"${strategy['total_profit']:.2f}"
            })
        
        df = pd.DataFrame(data)
        
        return html.Div([
            html.H3("📈 Strategy Performance", style={'marginBottom': '20px'}),
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([html.Th(col) for col in df.columns])
                    ]),
                    html.Tbody([
                        html.Tr([html.Td(str(df.iloc[i][col])) for col in df.columns])
                        for i in range(len(df))
                    ])
                ])
            ])
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def _create_trade_history_table(self):
        return html.Div([
            html.H3("📜 Recent Trade History", style={'marginBottom': '20px'}),
            dcc.Graph(id='trade-history-chart')
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def _create_daily_stats_chart(self):
        return html.Div([
            html.H3("📊 Daily Statistics", style={'marginBottom': '20px'}),
            dcc.Graph(id='daily-stats-chart')
        ], style={'backgroundColor': '#ecf0f1', 'padding': '20px',
                 'borderRadius': '10px', 'marginBottom': '20px'})
    
    def setup_callbacks(self):
        @self.app.callback(
            [Output('balance-chart', 'figure'),
             Output('trades-chart', 'figure'),
             Output('trade-history-chart', 'figure'),
             Output('daily-stats-chart', 'figure')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_charts(n):
            daily_stats = db_manager.get_daily_stats()
            
            balance_fig = self._create_balance_figure(daily_stats)
            trades_fig = self._create_trades_figure()
            history_fig = self._create_history_figure()
            stats_fig = self._create_daily_stats_figure(daily_stats)
            
            return balance_fig, trades_fig, history_fig, stats_fig
    
    def _create_balance_figure(self, daily_stats):
        if not daily_stats:
            return go.Figure()
        
        df = pd.DataFrame(daily_stats)
        df['end_balance'] = df['end_balance'].astype(float)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['end_balance'],
            mode='lines+markers',
            name='Balance',
            line=dict(color='#2ecc71', width=2)
        ))
        
        fig.update_layout(
            title='Balance Over Time',
            xaxis_title='Date',
            yaxis_title='Balance ($)',
            hovermode='x unified',
            margin=dict(l=0, r=0, t=30, b=0)
        )
        
        return fig
    
    def _create_trades_figure(self):
        trades = db_manager.get_trade_history(limit=50)
        
        if not trades:
            return go.Figure()
        
        df = pd.DataFrame(trades)
        df['profit'] = df['profit'].astype(float)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(range(len(df))),
            y=df['profit'],
            marker_color=['#27ae60' if p > 0 else '#e74c3c' for p in df['profit']]
        ))
        
        fig.update_layout(
            title='Recent Trade Results',
            xaxis_title='Trade',
            yaxis_title='Profit ($)',
            showlegend=False
        )
        
        return fig
    
    def _create_history_figure(self):
        trades = db_manager.get_trade_history(limit=20)
        
        if not trades:
            return go.Figure()
        
        df = pd.DataFrame(trades)
        df['cumulative_profit'] = df['profit'].astype(float).cumsum()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(df))),
            y=df['cumulative_profit'],
            mode='lines+markers',
            name='Cumulative Profit',
            line=dict(color='#3498db', width=2)
        ))
        
        fig.update_layout(
            title='Cumulative Profit (Last 20 Trades)',
            xaxis_title='Trade',
            yaxis_title='Cumulative Profit ($)',
            hovermode='x unified'
        )
        
        return fig
    
    def _create_daily_stats_figure(self, daily_stats):
        if not daily_stats:
            return go.Figure()
        
        df = pd.DataFrame(daily_stats)
        df['daily_profit'] = df['daily_profit'].astype(float)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['daily_profit'],
            marker_color=['#27ae60' if p > 0 else '#e74c3c' for p in df['daily_profit']]
        ))
        
        fig.update_layout(
            title='Daily Profit/Loss',
            xaxis_title='Date',
            yaxis_title='Daily Profit ($)',
            showlegend=False
        )
        
        return fig
    
    def run(self):
        logger.info(f"Starting dashboard on {config.DASHBOARD.HOST}:{config.DASHBOARD.PORT}")
        self.app.run_server(
            host=config.DASHBOARD.HOST,
            port=config.DASHBOARD.PORT,
            debug=config.DASHBOARD.DEBUG
        )


dashboard = Dashboard()
