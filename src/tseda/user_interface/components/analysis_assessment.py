"""Dash layout for the Time Series Decomposition (Step 2) analysis panel."""

from dash import dcc, html
import dash_bootstrap_components as dbc


def analysis_layout() -> html.Div:
    """Build and return the full Step-2 decomposition layout.

    The layout includes component grouping inputs, a signal reconstruction
    plot, a LOESS verification plot, a change-point plot, a W-correlation
    matrix image, and a reconstruction summary card.

    Returns:
        Dash ``html.Div`` containing the complete decomposition panel.
    """
    return html.Div([
        html.H3("Time Series Decomposition"),
        dbc.Container([
            # First Row: Eigen plots
            dbc.Row([
                dbc.Col(
                    dcc.Graph(id='eigen-plot', style={"height": "400px"}),
                    width=6
                ),
                dbc.Col(
                    html.Div([
                        html.H5("Variation Associated with Components", className="text-center mb-3"),
                        html.Img(id='eigenvector-plot', style={"width": "100%", "height": "400px", "objectFit": "contain"}),
                    ]),
                    width=6
                ),
            ], className="mb-4"),

            # Second Row: Component input panel
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Component Grouping", className="mb-0")),
                        dbc.CardBody([
                            dbc.Alert(
                                "Please review the eigen vector plot and the variation associated with the components. Each component has a number going from 0 to one less than the window size. In the table below, you can group the components into a set of up to 3 groups. In the first column, name the component, in the second column input the list of components that you think go into the definition of that component. For example, if you call a component, \"Trend\" and think components, 0,1,2 are associated with it. Put Trend in the first column and 0,1,2 in the second. For the Noise row, you can enter * to automatically assign all remaining indices. When you are done, press \"Apply Grouping\"",
                                color="info",
                                className="mb-3"
                            ),
                            dbc.Table([
                                html.Thead(html.Tr([
                                    html.Th("Component Name"),
                                    html.Th("Component List"),
                                ])),
                                html.Tbody([
                                    html.Tr([
                                        html.Td(dbc.Input(id='component-name-1', type='text', placeholder='e.g., Trend', className='form-control')),
                                        html.Td(dbc.Input(id='component-list-1', type='text', placeholder='e.g., 0,1', className='form-control'))
                                    ]),
                                    html.Tr([
                                        html.Td(dbc.Input(id='component-name-2', type='text', placeholder='e.g., Seasonal', className='form-control')),
                                        html.Td(dbc.Input(id='component-list-2', type='text', placeholder='e.g., 2,3', className='form-control'))
                                    ]),
                                    html.Tr([
                                        html.Td(dbc.Input(id='component-name-3', type='text', placeholder='e.g., Noise', className='form-control')),
                                        html.Td(dbc.Input(id='component-list-3', type='text', placeholder='e.g., 4,5 or *', className='form-control'))
                                    ]),
                                ]),
                            ], borderless=True, style={'width': '100%'}),
                            html.Div(id='component-validation-error', className='text-danger mt-2'),
                            dbc.Button("Apply Grouping", id='apply-components-btn', color='primary', className='mt-3'),
                            html.Div(id='noisy-series-message', className='mt-2'),
                            html.Hr(),
                            dbc.Label("SSA Window Size", html_for='ssa-window-slider', className='mt-2'),
                            dcc.Slider(
                                id='ssa-window-slider',
                                min=0,
                                max=0,
                                step=None,
                                value=0,
                                marks={},
                                tooltip={"placement": "bottom", "always_visible": False}
                            ),
                            html.Small(
                                "Valid values are integer multiples of the default window size (2W, 3W, ..., KW).",
                                className='text-muted d-block mt-2'
                            )
                        ])
                    ])
                ], width=12),
            ]),

            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H5("Signal Reconstruction", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id='signal-reconstruction-plot', style={"height": "400px"})
                        ])
                    ]),
                    width=12
                ),
            ], className="mt-4"),

            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H5("Verification Plot", className="mb-0")),
                        dbc.CardBody([
                            dbc.Label("LOESS Fraction", html_for='loess-fraction-slider', className='mt-1'),
                            dcc.Slider(
                                id='loess-fraction-slider',
                                min=0.05,
                                max=0.5,
                                step=0.05,
                                value=0.05,
                                marks={
                                    0.05: '0.05',
                                    0.1: '0.1',
                                    0.2: '0.2',
                                    0.3: '0.3',
                                    0.4: '0.4',
                                    0.5: '0.5',
                                },
                                tooltip={"placement": "bottom", "always_visible": False}
                            ),
                            html.Small(
                                "Adjust to verify LOESS smoothing against the raw preprocessed signal.",
                                className='text-muted d-block mt-2 mb-3'
                            ),
                            dcc.Graph(id='verification-plot', style={"height": "400px"})
                        ])
                    ]),
                    width=12
                ),
            ], className="mt-4"),

            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H5("Change Point Plot", className="mb-0")),
                        dbc.CardBody([
                            dcc.Graph(id='change-point-plot', style={"height": "400px"})
                        ])
                    ]),
                    width=12
                ),
            ], className="mt-4"),

            dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H5("W-Correlation Matrix", className="mb-0")),
                        dbc.CardBody([
                            html.Img(id='wcorr-plot', style={"width": "100%", "height": "400px", "objectFit": "contain"})
                        ])
                    ]),
                    width=6
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H5("Reconstruction Summary", className="mb-0")),
                        dbc.CardBody([
                            html.Div("Reconstruction metadata will appear here after applying grouping.", id='reconstruction-metadata', className='text-muted mb-3'),
                            dcc.Graph(id='noise-kde-plot', style={"height": "250px"}),
                        ])
                    ]),
                    width=6
                ),
            ], className="mt-4")
        ], fluid=True),
    ])
