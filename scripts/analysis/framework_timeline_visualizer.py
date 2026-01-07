#!/usr/bin/env python3
"""
Framework Timeline Visualizer

Creates visualization-ready data from framework timeline mapping.
Generates HTML timeline visualization.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logger
from src.utils.paths import get_analysis_dir

logger = setup_logger()


class FrameworkTimelineVisualizer:
    """Create visualizations from framework timeline."""
    
    def __init__(self):
        self.analysis_dir = get_analysis_dir()
        self.timeline_file = self.analysis_dir / 'framework_timeline.json'
        self.metrics_file = self.analysis_dir / 'framework_metrics_timeline.json'
    
    def generate_visualization(self):
        """Generate HTML visualization."""
        logger.info("Generating framework timeline visualization...")
        
        # Load timeline data
        if not self.timeline_file.exists():
            logger.error(f"Timeline file not found: {self.timeline_file}")
            return
        
        with open(self.timeline_file, 'r') as f:
            timeline = json.load(f)
        
        # Load metrics
        metrics = []
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                metrics = json.load(f)
        
        # Generate HTML
        html = self._generate_html(timeline, metrics)
        
        output_file = self.analysis_dir / 'framework_timeline_visualization.html'
        with open(output_file, 'w') as f:
            f.write(html)
        
        logger.info(f"Visualization saved to {output_file}")
        
        # Generate summary report
        self._generate_summary_report(timeline, metrics)
    
    def _generate_html(self, timeline: List[Dict], metrics: List[Dict]) -> str:
        """Generate HTML visualization."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Framework Timeline: Bitcoin Core Governance</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .timeline-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .timeline-table th, .timeline-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .timeline-table th {
            background-color: #4CAF50;
            color: white;
        }
        .timeline-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .metric-value {
            font-weight: bold;
            color: #2196F3;
        }
        .framework-badge {
            display: inline-block;
            padding: 2px 8px;
            margin: 2px;
            border-radius: 3px;
            font-size: 0.85em;
        }
        .multi-framework {
            background-color: #E3F2FD;
            color: #1976D2;
        }
        .earlier {
            background-color: #FFF3E0;
            color: #F57C00;
        }
        .chart-container {
            margin: 30px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Framework Timeline: Bitcoin Core Governance Evolution</h1>
        <p>This visualization shows how governance patterns evolved over time across all analytical frameworks.</p>
        
        <h2>Timeline Overview</h2>
        <table class="timeline-table">
            <thead>
                <tr>
                    <th>Year</th>
                    <th>Key Metrics</th>
                    <th>Active Frameworks</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Add timeline rows
        for entry in timeline:
            year = entry['year']
            metrics_str = self._format_metrics(entry.get('metrics', {}))
            frameworks_str = self._format_frameworks(entry.get('frameworks', {}))
            
            html += f"""
                <tr>
                    <td><strong>{year}</strong></td>
                    <td>{metrics_str}</td>
                    <td>{frameworks_str}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <h2>Metrics Over Time</h2>
        <div id="metrics-chart" class="chart-container"></div>
        
        <h2>Framework Coverage</h2>
        <div id="framework-chart" class="chart-container"></div>
    </div>
    
    <script>
        // Metrics chart data
        var metricsData = """
        html += json.dumps(metrics)
        html += """;
        
        // Prepare chart data
        var metricsTraces = [];
        if (metricsData.length > 0) {
            var metricKeys = Object.keys(metricsData[0]).filter(k => k !== 'year');
            
            metricKeys.forEach(function(key) {
                var trace = {
                    x: metricsData.map(d => d.year),
                    y: metricsData.map(d => d[key]),
                    name: key.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase()),
                    type: 'scatter',
                    mode: 'lines+markers'
                };
                metricsTraces.push(trace);
            });
        }
        
        var metricsLayout = {
            title: 'Governance Metrics Over Time',
            xaxis: { title: 'Year' },
            yaxis: { title: 'Metric Value' },
            hovermode: 'closest'
        };
        
        Plotly.newPlot('metrics-chart', metricsTraces, metricsLayout);
        
        // Framework coverage chart
        var frameworkData = """
        framework_counts = {}
        for entry in timeline:
            year = entry['year']
            count = len(entry.get('frameworks', {}))
            framework_counts[year] = count
        
        html += json.dumps([{'year': k, 'count': v} for k, v in sorted(framework_counts.items())])
        html += """;
        
        var frameworkTrace = {
            x: frameworkData.map(d => d.year),
            y: frameworkData.map(d => d.count),
            type: 'bar',
            marker: { color: '#4CAF50' },
            name: 'Active Frameworks'
        };
        
        var frameworkLayout = {
            title: 'Number of Active Frameworks by Year',
            xaxis: { title: 'Year' },
            yaxis: { title: 'Framework Count' }
        };
        
        Plotly.newPlot('framework-chart', [frameworkTrace], frameworkLayout);
    </script>
</body>
</html>
"""
        return html
    
    def _format_metrics(self, metrics: Dict) -> str:
        """Format metrics for display."""
        if not metrics:
            return "<em>No metrics</em>"
        
        formatted = []
        for key, value in list(metrics.items())[:5]:  # Limit to 5 metrics
            if isinstance(value, float):
                if value >= 1.0:
                    formatted.append(f"{key.replace('_', ' ').title()}: {value:.1%}")
                else:
                    formatted.append(f"{key.replace('_', ' ').title()}: {value:.3f}")
            else:
                formatted.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "<br>".join(formatted)
    
    def _format_frameworks(self, frameworks: Dict) -> str:
        """Format frameworks for display."""
        if not frameworks:
            return "<em>No frameworks</em>"
        
        badges = []
        for name, data in list(frameworks.items())[:5]:  # Limit to 5 frameworks
            category = data.get('category', 'unknown')
            badge_class = 'multi-framework' if category == 'multi_framework' else 'earlier'
            badges.append(f'<span class="framework-badge {badge_class}">{name}</span>')
        
        return " ".join(badges)
    
    def _generate_summary_report(self, timeline: List[Dict], metrics: List[Dict]):
        """Generate summary report."""
        output_file = self.analysis_dir / 'framework_timeline_summary.md'
        
        with open(output_file, 'w') as f:
            f.write("# Framework Timeline Summary\n\n")
            f.write("## Overview\n\n")
            f.write(f"- **Years Analyzed**: {len(timeline)}\n")
            f.write(f"- **Total Framework Observations**: {sum(len(e.get('frameworks', {})) for e in timeline)}\n")
            f.write(f"- **Metrics Tracked**: {len(metrics[0].keys()) - 1 if metrics else 0}\n\n")
            
            f.write("## Timeline Highlights\n\n")
            
            # Find years with most frameworks
            framework_counts = {e['year']: len(e.get('frameworks', {})) for e in timeline}
            top_years = sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            f.write("### Years with Most Framework Coverage\n\n")
            for year, count in top_years:
                f.write(f"- **{year}**: {count} frameworks active\n")
            
            f.write("\n## Key Metrics Evolution\n\n")
            
            if metrics:
                # Extract metric trends
                metric_trends = {}
                for metric_key in metrics[0].keys():
                    if metric_key != 'year':
                        values = [m[metric_key] for m in metrics if metric_key in m and m[metric_key] is not None]
                        if values:
                            metric_trends[metric_key] = {
                                'start': values[0],
                                'end': values[-1],
                                'change': values[-1] - values[0] if len(values) > 1 else 0
                            }
                
                f.write("| Metric | Start | End | Change |\n")
                f.write("|--------|-------|-----|--------|\n")
                for metric, trend in list(metric_trends.items())[:10]:
                    start_val = f"{trend['start']:.3f}" if isinstance(trend['start'], float) else str(trend['start'])
                    end_val = f"{trend['end']:.3f}" if isinstance(trend['end'], float) else str(trend['end'])
                    change_val = f"{trend['change']:+.3f}" if isinstance(trend['change'], float) else str(trend['change'])
                    f.write(f"| {metric.replace('_', ' ').title()} | {start_val} | {end_val} | {change_val} |\n")
        
        logger.info(f"Summary report saved to {output_file}")


def main():
    visualizer = FrameworkTimelineVisualizer()
    visualizer.generate_visualization()
    
    print("\n" + "="*60)
    print("Framework Timeline Visualization Complete")
    print("="*60)
    print("\nOutput files:")
    print("  - analysis/framework_timeline_visualization.html")
    print("  - analysis/framework_timeline_summary.md")


if __name__ == '__main__':
    main()

