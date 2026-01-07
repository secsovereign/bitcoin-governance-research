"""HTML template generator for visualizations."""

from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json


class HTMLTemplateGenerator:
    """Generates standalone HTML pages for visualizations."""
    
    # CDN URLs
    PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.26.0.min.js"
    VIS_NETWORK_CDN = "https://unpkg.com/vis-network@latest/standalone/umd/vis-network.min.js"
    
    def __init__(self, title: str = "Bitcoin Governance Analysis"):
        """Initialize template generator."""
        self.title = title
        self.primary_color = "#F7931A"  # Bitcoin orange
        self.secondary_color = "#0066CC"  # Blue
        self.neutral_color = "#1A1A1A"  # Dark gray
    
    def generate_plotly_page(
        self,
        plot_data: Dict[str, Any],
        title: str,
        output_path: Path,
        description: str = "",
        data_source: str = "Bitcoin Core Development Data"
    ) -> Path:
        """
        Generate standalone HTML page with Plotly.js chart.
        
        Args:
            plot_data: Plotly.js figure dictionary
            title: Chart title
            description: Chart description
            output_path: Output file path
            data_source: Data source citation
        """
        html = self._get_base_html()
        
        # Add Plotly.js
        html = html.replace('<!-- LIBRARIES -->', f'<script src="{self.PLOTLY_CDN}"></script>')
        
        # Add chart container
        chart_html = f'''
        <div class="container">
            <header>
                <h1>{title}</h1>
                <p class="description">{description}</p>
            </header>
            
            <div id="chart-container">
                <div id="plotly-chart"></div>
            </div>
            
            <footer>
                <p class="data-source">Data source: {data_source}</p>
                <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <nav>
                    <a href="../index.html">← Back to Visualizations</a>
                </nav>
            </footer>
        </div>
        '''
        
        html = html.replace('<!-- CONTENT -->', chart_html)
        
        # Add chart initialization script
        plot_data_json = json.dumps(plot_data, indent=2)
        script = f'''
        <script>
            const plotData = {plot_data_json};
            Plotly.newPlot('plotly-chart', plotData.data, plotData.layout, {{
                responsive: true,
                displayModeBar: true,
                modeBarButtonsToRemove: ['lasso2d', 'select2d'],
                toImageButtonOptions: {{
                    format: 'png',
                    filename: '{title.lower().replace(" ", "_")}',
                    height: 800,
                    width: 1200,
                    scale: 2
                }}
            }});
        </script>
        '''
        
        html = html.replace('<!-- SCRIPTS -->', script)
        
        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def generate_vis_network_page(
        self,
        nodes: list,
        edges: list,
        title: str,
        output_path: Path,
        description: str = "",
        data_source: str = "Bitcoin Core Development Data",
        options: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate standalone HTML page with vis-network graph.
        
        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            title: Chart title
            description: Chart description
            output_path: Output file path
            data_source: Data source citation
            options: Optional vis-network configuration
        """
        html = self._get_base_html()
        
        # Add vis-network
        html = html.replace('<!-- LIBRARIES -->', f'<script src="{self.VIS_NETWORK_CDN}"></script>')
        
        # Add network container
        chart_html = f'''
        <div class="container">
            <header>
                <h1>{title}</h1>
                <p class="description">{description}</p>
            </header>
            
            <div id="chart-container">
                <div id="network-chart"></div>
            </div>
            
            <div id="network-controls">
                <button onclick="resetZoom()">Reset Zoom</button>
                <button onclick="fitNetwork()">Fit Network</button>
            </div>
            
            <footer>
                <p class="data-source">Data source: {data_source}</p>
                <p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <nav>
                    <a href="../index.html">← Back to Visualizations</a>
                </nav>
            </footer>
        </div>
        '''
        
        html = html.replace('<!-- CONTENT -->', chart_html)
        
        # Default options
        if options is None:
            options = {
                'nodes': {
                    'shape': 'dot',
                    'scaling': {'min': 10, 'max': 30},
                    'font': {'size': 12}
                },
                'edges': {
                    'width': 2,
                    'smooth': {'type': 'continuous'}
                },
                'physics': {
                    'enabled': True,
                    'stabilization': {'iterations': 100}
                },
                'interaction': {
                    'hover': True,
                    'tooltipDelay': 200
                }
            }
        
        # Add network initialization script
        nodes_json = json.dumps(nodes, indent=2)
        edges_json = json.dumps(edges, indent=2)
        options_json = json.dumps(options, indent=2)
        
        script = f'''
        <script>
            const nodes = new vis.DataSet({nodes_json});
            const edges = new vis.DataSet({edges_json});
            const data = {{ nodes: nodes, edges: edges }};
            const options = {options_json};
            
            const container = document.getElementById('network-chart');
            const network = new vis.Network(container, data, options);
            
            function resetZoom() {{
                network.moveTo({{ scale: 1 }});
            }}
            
            function fitNetwork() {{
                network.fit();
            }}
            
            network.on("click", function (params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const node = nodes.get(nodeId);
                    console.log("Selected node:", node);
                }}
            }});
        </script>
        '''
        
        html = html.replace('<!-- SCRIPTS -->', script)
        
        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def generate_index_page(
        self,
        visualizations: list,
        output_path: Path
    ) -> Path:
        """
        Generate index page linking to all visualizations.
        
        Args:
            visualizations: List of dicts with 'title', 'path', 'description'
            output_path: Output file path
        """
        html = self._get_base_html()
        
        html = html.replace('<!-- LIBRARIES -->', '')
        
        # Build visualization list
        viz_list = '<ul class="visualization-list">'
        for viz in visualizations:
            viz_list += f'''
            <li>
                <a href="{viz['path']}">
                    <h3>{viz['title']}</h3>
                    <p>{viz.get('description', '')}</p>
                </a>
            </li>
            '''
        viz_list += '</ul>'
        
        content = f'''
        <div class="container">
            <header>
                <h1>Bitcoin Governance Analysis - Visualizations</h1>
                <p class="description">Interactive visualizations from the quantitative analysis of Bitcoin Core development governance.</p>
            </header>
            
            <nav class="category-nav">
                <a href="#power-concentration">Power Concentration</a>
                <a href="#maintainer-premium">Maintainer Premium</a>
                <a href="#decision-criteria">Decision Criteria</a>
                <a href="#transparency-gap">Transparency Gap</a>
                <a href="#communication-patterns">Communication Patterns</a>
            </nav>
            
            <main>
                {viz_list}
            </main>
            
            <footer>
                <p class="timestamp">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </footer>
        </div>
        '''
        
        html = html.replace('<!-- CONTENT -->', content)
        html = html.replace('<!-- SCRIPTS -->', '')
        
        # Write file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _get_base_html(self) -> str:
        """Get base HTML template with shared CSS."""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #fff;
        }}
        
        @media (prefers-color-scheme: dark) {{
            body {{
                background: #1a1a1a;
                color: #e0e0e0;
            }}
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid {self.primary_color};
        }}
        
        h1 {{
            color: {self.primary_color};
            margin-bottom: 10px;
        }}
        
        .description {{
            color: #666;
            font-size: 1.1em;
        }}
        
        @media (prefers-color-scheme: dark) {{
            .description {{
                color: #aaa;
            }}
        }}
        
        #chart-container {{
            margin: 30px 0;
            min-height: 600px;
        }}
        
        #network-chart {{
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        
        @media (prefers-color-scheme: dark) {{
            #network-chart {{
                border-color: #444;
            }}
        }}
        
        #network-controls {{
            margin: 20px 0;
            text-align: center;
        }}
        
        #network-controls button {{
            margin: 0 10px;
            padding: 10px 20px;
            background: {self.primary_color};
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }}
        
        #network-controls button:hover {{
            opacity: 0.9;
        }}
        
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
        
        @media (prefers-color-scheme: dark) {{
            footer {{
                border-color: #444;
                color: #aaa;
            }}
        }}
        
        .data-source {{
            margin-bottom: 5px;
        }}
        
        .timestamp {{
            margin-bottom: 10px;
        }}
        
        nav a {{
            color: {self.primary_color};
            text-decoration: none;
        }}
        
        nav a:hover {{
            text-decoration: underline;
        }}
        
        .visualization-list {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        
        .visualization-list li {{
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 20px;
            transition: transform 0.2s;
        }}
        
        .visualization-list li:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .visualization-list a {{
            text-decoration: none;
            color: inherit;
        }}
        
        .visualization-list h3 {{
            color: {self.primary_color};
            margin-bottom: 10px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            #network-chart {{
                height: 600px;
            }}
            
            .visualization-list {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
    <!-- LIBRARIES -->
</head>
<body>
    <!-- CONTENT -->
    <!-- SCRIPTS -->
</body>
</html>'''

