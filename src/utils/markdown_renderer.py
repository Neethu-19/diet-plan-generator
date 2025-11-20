"""
Markdown to HTML Renderer
Converts structured meal plan presentations to HTML
"""
import re
from typing import Dict, List
from src.models.schemas import EnhancedMealPlanResponse, MealPlanSection


class MarkdownRenderer:
    """Renders markdown content to HTML."""
    
    @staticmethod
    def render_to_html(enhanced_plan: EnhancedMealPlanResponse) -> str:
        """
        Convert enhanced meal plan to HTML.
        
        Args:
            enhanced_plan: Enhanced meal plan response
            
        Returns:
            HTML string
        """
        html_parts = []
        
        # Add summary
        html_parts.append(f'<div class="meal-plan-summary">')
        html_parts.append(f'<p class="summary-text">{enhanced_plan.summary}</p>')
        html_parts.append('</div>')
        
        # Add sections
        for section in enhanced_plan.sections:
            html_parts.append(MarkdownRenderer._render_section(section))
        
        # Add audience notes if present
        if enhanced_plan.target_audience_notes:
            html_parts.append('<div class="audience-notes">')
            html_parts.append(MarkdownRenderer._markdown_to_html(
                enhanced_plan.target_audience_notes
            ))
            html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    @staticmethod
    def _render_section(section: MealPlanSection) -> str:
        """Render a single section to HTML."""
        html = f'<div class="meal-section">'
        html += f'<h3 class="section-title">{section.title}</h3>'
        html += f'<div class="section-body">'
        html += MarkdownRenderer._markdown_to_html(section.body_markdown)
        html += '</div>'
        
        # Add tips if present
        if section.tips:
            html += '<div class="section-tips">'
            html += '<ul class="tips-list">'
            for tip in section.tips:
                html += f'<li>{tip}</li>'
            html += '</ul>'
            html += '</div>'
        
        html += '</div>'
        return html
    
    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        """
        Convert markdown to HTML (simple implementation).
        
        Args:
            markdown: Markdown text
            
        Returns:
            HTML string
        """
        html = markdown
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Tables (simple)
        lines = html.split('\n')
        in_table = False
        result = []
        
        for line in lines:
            if '|' in line and not line.strip().startswith('|---'):
                if not in_table:
                    result.append('<table class="nutrition-table">')
                    in_table = True
                
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if result[-1] == '<table class="nutrition-table">':
                    result.append('<thead><tr>')
                    for cell in cells:
                        result.append(f'<th>{cell}</th>')
                    result.append('</tr></thead><tbody>')
                else:
                    result.append('<tr>')
                    for cell in cells:
                        result.append(f'<td>{cell}</td>')
                    result.append('</tr>')
            elif line.strip().startswith('|---'):
                continue
            else:
                if in_table:
                    result.append('</tbody></table>')
                    in_table = False
                if line.strip():
                    result.append(f'<p>{line}</p>')
        
        if in_table:
            result.append('</tbody></table>')
        
        return '\n'.join(result)
