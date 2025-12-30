import sys
import os
import traceback
import pandas as pd
import numpy as np
import webbrowser
import tempfile
import json
import html
import types
import msvcrt

# --- CONFIGURATION ---
# Target HTML size per variable.
# This allows significantly more data to be displayed while preventing 
# multi-gigabyte crashes.
TARGET_BYTES_PER_VAR = 15 * 1024 * 1024  # 15 MB per variable

# Absolute hard ceiling for rows.
ABSOLUTE_ROW_LIMIT = 200000

# --- 1. HELPER FUNCTIONS ---

def get_preview_info(val):
    try:
        if isinstance(val, (pd.DataFrame, pd.Series)):
            return f"Shape: {val.shape}"
        elif isinstance(val, np.ndarray):
            base = f"Shape: {val.shape}"
            if val.size > 0 and np.issubdtype(val.dtype, np.number):
                try:
                    mn, mx = np.min(val), np.max(val)
                    if isinstance(mn, (float, np.floating)):
                        return f"{base} | Min: {mn:.2f}, Max: {mx:.2f}"
                    return f"{base} | Min: {mn}, Max: {mx}"
                except: pass
            return base
        elif isinstance(val, list):
            base = f"Length: {len(val)}"
            if len(val) > 0:
                try:
                    if all(isinstance(x, (int, float)) for x in val):
                        mn, mx = min(val), max(val)
                        if isinstance(mn, float):
                            return f"{base} | Min: {mn:.2f}, Max: {mx:.2f}"
                        return f"{base} | Min: {mn}, Max: {mx}"
                except: pass
            return base
        elif isinstance(val, dict):
            return f"Length: {len(val)}"
        elif isinstance(val, (int, float)):
            return f"Value: {val}"
        elif isinstance(val, str):
            preview = (val[:20] + '...') if len(val) > 20 else val
            return f'"{preview}"'
        else:
            return "-"
    except Exception:
        return "-"

def estimate_df_limit(df):
    """
    Calculates how many rows we can display based on the byte budget.
    """
    total_rows = df.shape[0]
    if total_rows == 0: return 0
    
    # Sample first 5 rows to get average bytes per row
    sample_size = min(5, total_rows)
    sample_html = df.head(sample_size).to_html(border=0)
    
    # Rough length of just the table syntax overhead
    overhead = 100 
    bytes_per_row = (len(sample_html) - overhead) / sample_size
    
    if bytes_per_row <= 0: bytes_per_row = 1 # Prevent divide by zero
    
    estimated_limit = int(TARGET_BYTES_PER_VAR / bytes_per_row)
    
    # Clamp between a minimum (50) and the absolute max
    return max(50, min(estimated_limit, ABSOLUTE_ROW_LIMIT))

# --- 2. CORE LOGIC ---

def format_array(arr):
    if arr.ndim <= 2:
        truncated = False
        display_arr = arr
        
        # Create a temporary DF just to calculate limits using the shared logic
        if arr.ndim == 1: 
            temp_df = pd.DataFrame(arr[:10], columns=['Value'])
        else: 
            temp_df = pd.DataFrame(arr[:10])
            
        limit = estimate_df_limit(temp_df)
        
        if arr.shape[0] > limit:
            display_arr = arr[:limit]
            truncated = True

        if display_arr.ndim == 1: 
            df = pd.DataFrame(display_arr, columns=['Value'])
        else: 
            df = pd.DataFrame(display_arr)
            
        html_out = df.to_html(classes='styled-table heatmap-table', border=0)
        
        if truncated:
            html_out += f"<div style='padding:5px; color:#75715e; font-style:italic'>(Showing first {limit} rows of {arr.shape[0]} - Limited by display size)</div>"
        return html_out
    else:
        max_slices = 50
        sliced_dict = {}
        for i in range(min(arr.shape[0], max_slices)):
            label = f"Slice {i}"
            sub_val = arr[i]
            sliced_dict[label] = sub_val 
        if arr.shape[0] > max_slices:
            sliced_dict["..."] = f"And {arr.shape[0] - max_slices} more slices..."
        return sliced_dict

def render_recursive_html(data, level=0):
    html_str = '<ul class="tree">'
    
    iterator = data.items() if isinstance(data, dict) else enumerate(data)
    count = 0
    current_html_len = 0
    total_len = len(data)
    
    for key, val in iterator:
        # DYNAMIC LIMIT: Check if we have exceeded the byte budget for this list
        if current_html_len > TARGET_BYTES_PER_VAR:
            remaining = total_len - count
            html_str += f'<li style="color: #75715e; font-style: italic; margin-top:5px;">... and {remaining} more items (truncated for performance) ...</li>'
            break
        
        count += 1
        item_html = '<li>'
        
        if isinstance(val, (pd.DataFrame, pd.Series)):
            df = val if isinstance(val, pd.DataFrame) else val.to_frame()
            
            limit = estimate_df_limit(df)
            
            if df.shape[0] > limit:
                table_html = df.head(limit).to_html(classes='styled-table heatmap-table', border=0)
                table_html += f"<div style='padding:5px; color:#75715e'>(Showing first {limit} rows of {df.shape[0]})</div>"
            else:
                table_html = df.to_html(classes='styled-table heatmap-table', border=0)
                
            shape = f"({df.shape[0]}x{df.shape[1]})"
            item_html += f'<details><summary><span class="key">{key}</span> <span class="meta type-tag">DataFrame {shape}</span></summary>'
            item_html += f'<div class="table-wrapper">{table_html}</div>'
            item_html += '</details>'
            
        elif isinstance(val, np.ndarray):
            formatted = format_array(val)
            if isinstance(formatted, dict):
                shape = str(val.shape)
                item_html += f'<details><summary><span class="key">{key}</span> <span class="meta type-tag">Array {shape}</span></summary>'
                item_html += render_recursive_html(formatted, level + 1)
                item_html += '</details>'
            else:
                shape = str(val.shape)
                item_html += f'<details><summary><span class="key">{key}</span> <span class="meta type-tag">Array {shape}</span></summary>'
                item_html += f'<div class="table-wrapper">{formatted}</div>'
                item_html += '</details>'
                
        elif isinstance(val, (dict, list)):
            item_count = len(val)
            open_attr = "open" if level < 1 else ""
            item_html += f'<details {open_attr}><summary><span class="key">{key}</span> <span class="meta">[{item_count} items]</span></summary>'
            item_html += render_recursive_html(val, level + 1)
            item_html += '</details>'
            
        elif isinstance(val, str) and val.strip().startswith('<table'):
             item_html += f'<details><summary><span class="key">{key}</span> <span class="meta">[Table Slice]</span></summary>'
             item_html += f'<div class="table-wrapper">{val}</div>'
             item_html += '</details>'
        else:
            safe_val = html.escape(str(val))
            item_html += f'<div class="row-item"><span class="key">{key}: </span><span class="val">{safe_val}</span></div>'
        
        item_html += '</li>'
        
        # Accumulate size to check against budget
        current_html_len += len(item_html)
        html_str += item_html
    
    html_str += '</ul>'
    return html_str

def show(local_vars):
    data_store = {}
    summary_list = []
    
    for name, val in local_vars.items():
        if name.startswith('_'): continue
        if hasattr(val, '__call__'): continue
        if isinstance(val, types.ModuleType): continue 
        if name in ['var_viper', 'pd', 'np', 'sys', 'os', 'html', 'json', 'tempfile', 'webbrowser', 'types', 'traceback']: continue 
        
        type_name = type(val).__name__
        size_info = get_preview_info(val)
        content_html = ""

        try:
            if isinstance(val, (pd.DataFrame, pd.Series)):
                df = val if isinstance(val, pd.DataFrame) else val.to_frame()
                
                limit = estimate_df_limit(df)
                
                if df.shape[0] > limit:
                    html_table = df.head(limit).to_html(classes='styled-table heatmap-table', border=0)
                    html_table += f"<div style='padding:10px; color:#75715e; font-style:italic'>(Showing first {limit} rows of {df.shape[0]} - Limited by display size)</div>"
                    content_html = html_table
                else:
                    content_html = df.to_html(classes='styled-table heatmap-table', border=0)
                    
            elif isinstance(val, np.ndarray):
                formatted_data = format_array(val)
                if isinstance(formatted_data, dict):
                    content_html = f"<div class='tree-wrapper'>{render_recursive_html(formatted_data)}</div>"
                else:
                    content_html = formatted_data
            elif isinstance(val, (dict, list)):
                content_html = f"<div class='tree-wrapper'>{render_recursive_html(val)}</div>"
            else:
                content_html = f"<div class='text-box'>{html.escape(str(val))}</div>"
        except Exception as e:
            content_html = f"<div class='error-box'>Error processing variable '{name}': {e}</div>"

        summary_list.append({"id": name, "type": type_name, "size": size_info})
        data_store[name] = content_html

    generate_html(summary_list, data_store)

def generate_html(summary_list, data_store):
    filename = "var_viper_view.html"
    filepath = os.path.join(tempfile.gettempdir(), filename)
    json_vars = json.dumps(summary_list)
    json_content = json.dumps(data_store)

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <title>Var Viper</title>
        <style id="viper-styles">
            /* --- MONOKAI THEME --- */
            :root {{ 
                --bg: #272822; 
                --sidebar-bg: #1e1f1c;
                --fg: #f8f8f2; 
                --border: #49483e;
                --accent-pink: #f92672;
                --accent-blue: #66d9ef;
                --accent-green: #a6e22e;
                --accent-yellow: #e6db74;
                --selection: #49483e;
                --table-head: #66d9ef; 
                --table-head-text: #272822;
            }}
            * {{ box-sizing: border-box; }}
            body {{ font-family: 'Consolas', 'Monaco', 'Courier New', monospace; margin: 0; height: 100vh; overflow: hidden; display: flex; background: var(--bg); color: var(--fg); }}
            
            /* --- LAYOUT --- */
            #sidebar {{ width: 300px; min-width: 150px; max-width: 50%; background: var(--sidebar-bg); display: flex; flex-direction: column; }}
            
            /* SIDEBAR RESIZER */
            #sidebar-resizer {{
                width: 6px;
                background-color: var(--bg);
                border-left: 1px solid var(--border);
                border-right: 1px solid var(--border);
                cursor: col-resize;
                user-select: none;
                transition: background-color 0.2s;
                z-index: 10;
            }}
            #sidebar-resizer:hover, #sidebar-resizer.resizing {{ background-color: var(--accent-pink); }}

            #content {{ flex: 1; overflow: hidden; display: flex; flex-direction: column; background: var(--bg); }}
            
            .sidebar-header {{ 
                padding: 15px; 
                background: #171814; 
                font-weight: bold; 
                border-bottom: 1px solid var(--border); 
                color: var(--accent-green); 
                letter-spacing: 1px; 
                white-space: nowrap; 
                overflow: hidden; 
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            #sort-select {{
                background: #3e3d32;
                color: #f8f8f2;
                border: 1px solid #49483e;
                border-radius: 4px;
                font-size: 0.8em;
                padding: 4px;
                outline: none;
                cursor: pointer;
                margin-left: 10px;
            }}
            #var-list {{ overflow-y: auto; flex: 1; }}
            #viewer-header {{ padding: 15px; border-bottom: 1px solid var(--border); background: var(--sidebar-bg); font-size: 1.2em; font-weight: bold; height: 60px; display: flex; align-items: center; color: var(--accent-blue); }}
            #viewer-body {{ flex: 1; overflow: auto; padding: 20px; position: relative; }}

            /* --- SIDEBAR ITEMS --- */
            /* REDUCED PADDING AND FONT SIZE FOR COMPACT VIEW */
            .var-item {{ padding: 6px 10px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.1s; overflow: hidden; }}
            .var-item:hover {{ background: #3e3d32; }}
            .var-item.active {{ background: var(--selection); border-left: 4px solid var(--accent-pink); padding-left: 6px; }}
            .var-item .header-row {{ display: flex; justify-content: space-between; align-items: center; }}
            .var-item .type-tag {{ font-size: 0.7em; background: var(--border); padding: 2px 6px; border-radius: 4px; color: var(--accent-blue); flex-shrink: 0; margin-left: 5px; }}
            .var-item.active .type-tag {{ background: var(--accent-pink); color: white; }}
            .var-item strong {{ color: var(--fg); font-size: 0.9em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .var-item .meta {{ font-size: 0.75em; color: #75715e; margin-top: 2px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

            /* --- TABLES --- */
            .table-wrapper {{ overflow: auto; max-height: 700px; border: 1px solid var(--border); margin-top: 5px; background: #272822; }}
            .styled-table {{
                border-collapse: collapse;
                font-size: 0.9em;
                width: auto;
                min-width: 100%;
                table-layout: auto;
            }}
            .styled-table th {{ background-color: var(--table-head); color: var(--table-head-text); position: sticky; top: 0; z-index: 2; padding: 10px; text-align: left; border-right: 1px solid rgba(0,0,0,0.1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; position: relative; }}
            .styled-table td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); border-right: 1px solid var(--border); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--fg); }}
            .styled-table td[style*="background-color"] {{ color: white; text-shadow: 0px 0px 2px black; }}

            .col-resizer {{ position: absolute; right: 0; top: 0; height: 100%; width: 5px; cursor: col-resize; user-select: none; touch-action: none; opacity: 0; }}
            .styled-table th:hover .col-resizer {{ opacity: 1; background-color: rgba(0,0,0,0.2); }}
            .col-resizer.resizing {{ opacity: 1; background-color: var(--accent-pink); }}

            /* --- TREE VIEW --- */
            .tree-wrapper {{ font-family: Consolas, monospace; font-size: 0.95em; }}
            ul.tree {{ list-style: none; padding-left: 20px; margin: 0; }}
            ul.tree li {{ margin: 6px 0; }}
            details > summary {{ list-style: none; cursor: pointer; outline: none; color: var(--accent-blue); }}
            details > summary::-webkit-details-marker {{ display: none; }}
            details summary::before {{ content: '▶'; display: inline-block; margin-right: 6px; font-size: 0.8em; color: var(--border); transition: transform 0.1s; }}
            details[open] > summary::before {{ transform: rotate(90deg); color: var(--accent-pink); }}
            .key {{ color: var(--accent-pink); font-weight: bold; }}
            .val {{ color: var(--accent-yellow); white-space: pre-wrap; word-break: break-word; }}
            .meta {{ color: #75715e; font-size: 0.85em; font-style: italic; }}
            .row-item {{ padding-left: 20px; }}

            .text-box {{ font-size: 1.5em; padding: 30px; background: var(--sidebar-bg); border: 1px solid var(--border); border-radius: 8px; display: inline-block; white-space: pre-wrap; color: var(--accent-yellow); min-width: 200px; text-align: center; }}
            .error-box {{ color: #ff4444; background-color: #330000; border: 1px solid red; padding: 15px; }}
            .placeholder {{ text-align: center; color: #75715e; margin-top: 20vh; }}
            
            /* --- PLOT STYLES --- */
            .selected-cell {{ box-shadow: inset 0 0 0 2px var(--accent-pink); background-color: rgba(249, 38, 114, 0.2) !important; }}
            #plot-btn {{ 
                position: fixed; bottom: 20px; right: 20px; 
                background: var(--accent-pink); color: white; border: none; 
                padding: 10px 20px; border-radius: 4px; cursor: pointer; 
                font-weight: bold; display: none; z-index: 100; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.3); font-size: 14px;
            }}
            #plot-btn:hover {{ background: #ff4081; }}
        </style>
    </head>
    <body>
        <div id="sidebar">
            <div class="sidebar-header">
                <span>VAR VIPER 🐍</span>
                <select id="sort-select" title="Sort Variables">
                    <option value="created">Created ↓</option>
                    <option value="created-desc">Created ↑</option>
                    <option value="alpha">Name (A-Z)</option>
                    <option value="alpha-desc">Name (Z-A)</option>
                </select>
            </div>
            <div id="var-list"></div>
        </div>
        <div id="sidebar-resizer"></div>
        <div id="content">
            <div id="viewer-header">Variable Explorer</div>
            <div id="viewer-body">
                <div class="placeholder">
                    <h2>Select a variable to inspect</h2>
                </div>
            </div>
        </div>

        <!-- PLOT UI -->
        <button id="plot-btn" onclick="plotData()">Plot Selection</button>

        <script>
            const variables = {json_vars};
            const contentData = {json_content};

            const listEl = document.getElementById('var-list');
            const headerEl = document.getElementById('viewer-header');
            const bodyEl = document.getElementById('viewer-body');
            const sortSelect = document.getElementById('sort-select');

            // Global State for Selection
            let isMouseDown = false;
            let startCell = null;
            let activeTable = null;

            // Initial rendering
            renderList(variables);

            sortSelect.addEventListener('change', () => {{
                const mode = sortSelect.value;
                let sorted = [...variables];
                
                if (mode === 'alpha') {{
                    sorted.sort((a, b) => a.id.localeCompare(b.id));
                }} else if (mode === 'alpha-desc') {{
                    sorted.sort((a, b) => b.id.localeCompare(a.id));
                }} else if (mode === 'created-desc') {{
                    sorted.reverse();
                }}
                renderList(sorted);
            }});

            function renderList(items) {{
                listEl.innerHTML = '';
                items.forEach(v => {{
                    const div = document.createElement('div');
                    div.className = 'var-item';
                    if (headerEl.textContent === v.id) {{
                        div.classList.add('active');
                    }}
                    div.innerHTML = `
                        <div class="header-row"><strong>${{v.id}}</strong><span class="type-tag">${{v.type}}</span></div>
                        <div class="meta">${{v.size}}</div>
                    `;
                    div.onclick = () => loadVariable(v.id, div);
                    div.ondblclick = () => popOutVariable(v.id);
                    listEl.appendChild(div);
                }});
            }}

            function loadVariable(id, element) {{
                document.querySelectorAll('.var-item').forEach(el => el.classList.remove('active'));
                if(element) element.classList.add('active');
                headerEl.textContent = id;
                bodyEl.innerHTML = contentData[id];
                const tables = bodyEl.querySelectorAll('table');
                tables.forEach(table => {{
                    makeColResizable(table);
                    if(table.classList.contains('heatmap-table')) applyHeatmap(table);
                    makeTableSelectable(table);
                }});
                updatePlotButton();
            }}

            // --- PLOTTING LOGIC ---
            
            function makeTableSelectable(table) {{
                // CELL SELECTION (Existing)
                const cells = table.querySelectorAll('td');
                cells.forEach(cell => {{
                    cell.style.userSelect = 'none'; 
                    cell.addEventListener('mousedown', (e) => {{
                        if (e.button !== 0) return;
                        isMouseDown = true;
                        startCell = cell;
                        activeTable = table;
                        document.querySelectorAll('.selected-cell').forEach(c => c.classList.remove('selected-cell'));
                        cell.classList.add('selected-cell');
                        updatePlotButton();
                    }});
                    cell.addEventListener('mouseover', () => {{
                        if (isMouseDown && activeTable === table && startCell) {{
                            selectRange(table, startCell, cell);
                        }}
                    }});
                }});
                
                // HEADER SELECTION (Rows/Cols)
                const headers = table.querySelectorAll('th');
                headers.forEach(th => {{
                    th.style.cursor = 'pointer';
                    th.title = "Click to select row/column";
                    
                    th.addEventListener('click', (e) => {{
                        // Ignore clicks on resizer
                        if(e.target.classList.contains('col-resizer')) return;
                        
                        // Clear existing selection
                        document.querySelectorAll('.selected-cell').forEach(c => c.classList.remove('selected-cell'));
                        
                        const row = th.parentElement;
                        const tableSection = row.parentElement; // thead or tbody
                        
                        if (tableSection.tagName === 'THEAD') {{
                            // Column Select
                            const colIdx = th.cellIndex;
                            const rows = table.querySelectorAll('tbody tr');
                            rows.forEach(r => {{
                                const cell = r.children[colIdx];
                                if (cell && cell.tagName === 'TD') {{
                                    cell.classList.add('selected-cell');
                                }}
                            }});
                        }} else {{
                            // Row Select (th is index)
                            const rowCells = row.querySelectorAll('td');
                            rowCells.forEach(c => c.classList.add('selected-cell'));
                        }}
                        updatePlotButton();
                    }});
                }});
            }}

            function selectRange(table, start, end) {{
                const startRow = start.parentElement.rowIndex;
                const endRow = end.parentElement.rowIndex;
                const startCol = start.cellIndex;
                const endCol = end.cellIndex;
                const minRow = Math.min(startRow, endRow);
                const maxRow = Math.max(startRow, endRow);
                const minCol = Math.min(startCol, endCol);
                const maxCol = Math.max(startCol, endCol);

                document.querySelectorAll('.selected-cell').forEach(c => c.classList.remove('selected-cell'));

                for (let r = minRow; r <= maxRow; r++) {{
                    const row = table.rows[r];
                    if (!row) continue;
                    for (let c = minCol; c <= maxCol; c++) {{
                        const cell = row.cells[c];
                        if (cell && cell.tagName === 'TD') {{
                            cell.classList.add('selected-cell');
                        }}
                    }}
                }}
                updatePlotButton();
            }}

            function updatePlotButton() {{
                const count = document.querySelectorAll('.selected-cell').length;
                const btn = document.getElementById('plot-btn');
                if (count > 1) {{
                    btn.style.display = 'block';
                    btn.textContent = `Plot ${{count}} points`;
                }} else {{
                    btn.style.display = 'none';
                }}
            }}
            
            function copySelection(e) {{
                if ((e.ctrlKey || e.metaKey) && e.key === 'c') {{
                    const selected = document.querySelectorAll('.selected-cell');
                    if (selected.length === 0) return;
                    e.preventDefault();
                    
                    // Group by Row
                    const rows = {{}};
                    selected.forEach(cell => {{
                        const r = cell.parentElement.rowIndex;
                        if(!rows[r]) rows[r] = [];
                        rows[r].push(cell);
                    }});
                    
                    // Sort and Format
                    const rowIndices = Object.keys(rows).sort((a,b)=>a-b);
                    const tsv = rowIndices.map(idx => {{
                        const cells = rows[idx];
                        cells.sort((a,b)=>a.cellIndex - b.cellIndex);
                        return cells.map(c=>c.textContent.trim()).join('\\t');
                    }}).join('\\n');
                    
                    const ta = document.createElement('textarea');
                    ta.value = tsv;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    
                    // Feedback
                    const btn = document.getElementById('plot-btn');
                    if(btn && btn.style.display !== 'none') {{
                        const orig = btn.textContent;
                        btn.textContent = "Copied!";
                        setTimeout(()=>btn.textContent = orig, 1000);
                    }}
                }}
            }}
            
            document.addEventListener('keydown', copySelection);

            function plotData() {{
                const cells = document.querySelectorAll('.selected-cell');
                let data = [];
                cells.forEach(c => {{
                    const txt = c.textContent.trim();
                    if(txt && txt !== 'NaN' && txt !== 'None') {{
                        const val = parseFloat(txt);
                        if (!isNaN(val)) data.push(val);
                    }}
                }});
                
                if (data.length < 2) return alert("Select at least 2 numeric values to plot.");

                const win = window.open("", "_blank", "width=800,height=600");
                win.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Data Plot</title>
                        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"><\\/script>
                        <style>
                            body {{ background: #272822; color: #f8f8f2; margin: 0; padding: 0; overflow: hidden; font-family: sans-serif; }}
                            #chart {{ width: 100vw; height: 100vh; }}
                        </style>
                    </head>
                    <body>
                        <div id="chart"></div>
                        <script>
                            const data = ${{JSON.stringify(data)}};
                            const trace = {{
                                y: data,
                                mode: 'lines',
                                type: 'scatter',
                                line: {{ width: 1, color: '#66d9ef' }}
                            }};
                            const layout = {{
                                paper_bgcolor: '#272822',
                                plot_bgcolor: '#272822',
                                font: {{ color: '#f8f8f2' }},
                                margin: {{ t: 50, r: 20, l: 50, b: 50 }},
                                xaxis: {{ gridcolor: '#49483e', zerolinecolor: '#49483e' }},
                                yaxis: {{ gridcolor: '#49483e', zerolinecolor: '#49483e' }},
                                title: 'Selected Data Plot'
                            }};
                            Plotly.newPlot('chart', [trace], layout, {{responsive: true}});
                        <\\/script>
                    </body>
                    </html>
                `);
                win.document.close();
            }}
            
            document.addEventListener('mouseup', () => {{ isMouseDown = false; }});


            function popOutVariable(id) {{
                const content = contentData[id];
                // Use ID to reliably get the styles even if other style tags exist
                const styles = document.getElementById('viper-styles').innerHTML;
                const win = window.open("", "_blank", "width=900,height=700");
                if (!win) return alert("Pop-up blocked!");
                
                // Get function sources to inject
                const applyHeatmapSrc = applyHeatmap.toString();
                const makeColResizableSrc = makeColResizable.toString();
                const makeTableSelectableSrc = makeTableSelectable.toString();
                const selectRangeSrc = selectRange.toString();
                const updatePlotButtonSrc = updatePlotButton.toString();
                const plotDataSrc = plotData.toString();
                const copySelectionSrc = copySelection.toString();

                win.document.write(`
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                        <meta charset="UTF-8">
                        <title>${{id}} - Var Viper</title>
                        <style>${{styles}}</style>
                        <style>
                            body {{ overflow: auto; padding: 0; background: var(--bg); height: 100vh; display: flex; flex-direction: column; }}
                            .table-wrapper {{ border: none; max-height: none; flex: 1; margin: 0; }}
                            #popout-container {{ padding: 20px; flex: 1; display: flex; flex-direction: column; }}
                            h2 {{ margin-top: 0; color: var(--accent-pink); }}
                        </style>
                    </head>
                    <body>
                        <div id="popout-container">
                            <h2>${{id}}</h2>
                            ${{content}}
                        </div>

                        <!-- Plot Button -->
                        <button id="plot-btn" onclick="plotData()">Plot Selection</button>

                        <script>
                            // Global State for Popout
                            let isMouseDown = false;
                            let startCell = null;
                            let activeTable = null;

                            // Inject shared helper functions
                            ${{applyHeatmapSrc}}
                            ${{makeColResizableSrc}}
                            ${{makeTableSelectableSrc}}
                            ${{selectRangeSrc}}
                            ${{updatePlotButtonSrc}}
                            ${{plotDataSrc}}
                            ${{copySelectionSrc}}
                            
                            // Initialize interactivity in popout
                            const bodyEl = document.getElementById('popout-container');
                            const tables = bodyEl.querySelectorAll('table');
                            tables.forEach(table => {{
                                makeColResizable(table);
                                if(table.classList.contains('heatmap-table')) applyHeatmap(table);
                                makeTableSelectable(table);
                            }});
                            
                            document.addEventListener('mouseup', () => {{ isMouseDown = false; }});
                            document.addEventListener('keydown', copySelection);
                        <\\/script>
                    </body>
                    </html>
                `);
                win.document.close();
            }}

            function applyHeatmap(table) {{
                const rows = Array.from(table.querySelectorAll('tbody tr'));
                if(rows.length === 0) return;
                const colCount = rows[0].children.length;
                
                let allValues = [];
                let allCells = [];

                // Pass 1: Gather all numeric data from valid numeric columns
                for(let c=1; c < colCount; c++) {{
                    let colValues = [], colCells = [], isNumeric = true;
                    for(let r=0; r < rows.length; r++) {{
                        const cell = rows[r].children[c];
                        const txt = cell.textContent.trim();
                        if(txt === '' || txt === 'NaN' || txt === 'None') continue;
                        const num = parseFloat(txt);
                        if(isNaN(num)) {{ isNumeric = false; break; }}
                        colValues.push(num);
                        colCells.push({{el: cell, val: num}});
                    }}
                    
                    if(isNumeric && colValues.length > 0) {{
                        allValues = allValues.concat(colValues);
                        allCells = allCells.concat(colCells);
                    }}
                }}

                // Pass 2: Calculate Global Range and Apply Color
                if(allValues.length === 0) return;
                const min = Math.min(...allValues);
                const max = Math.max(...allValues);
                if(min === max) return;

                allCells.forEach(item => {{
                    const ratio = (item.val - min) / (max - min);
                    const red = Math.round(255 * ratio);
                    const blue = Math.round(255 * (1 - ratio));
                    item.el.style.backgroundColor = `rgba(${{red}}, 0, ${{blue}}, 0.7)`;
                }});
            }}

            function makeColResizable(table) {{
                const headers = table.querySelectorAll('th');
                headers.forEach(th => {{
                    if(th.querySelector('.col-resizer')) return;
                    const resizer = document.createElement('div');
                    resizer.classList.add('col-resizer');
                    th.appendChild(resizer);
                    let x = 0; let w = 0;

                    const md = function(e) {{
                        x = e.clientX;
                        w = parseInt(window.getComputedStyle(th).width, 10);
                        document.addEventListener('mousemove', mm);
                        document.addEventListener('mouseup', mu);
                        resizer.classList.add('resizing');
                        e.stopPropagation(); // Prevent sort or other events
                    }};

                    const mm = function(e) {{
                        th.style.width = `${{w + (e.clientX - x)}}px`;
                    }};

                    const mu = function() {{
                        document.removeEventListener('mousemove', mm);
                        document.removeEventListener('mouseup', mu);
                        resizer.classList.remove('resizing');
                    }};

                    resizer.addEventListener('mousedown', md);
                    resizer.addEventListener('click', (e) => e.stopPropagation()); // Prevent click-through
                }});
            }}

            // --- SIDEBAR RESIZE LOGIC ---
            (function() {{
                const sidebar = document.getElementById('sidebar');
                const resizer = document.getElementById('sidebar-resizer');
                let x = 0; let w = 0;
                const md = function(e) {{
                    x = e.clientX;
                    w = parseInt(window.getComputedStyle(sidebar).width, 10);
                    document.addEventListener('mousemove', mm);
                    document.addEventListener('mouseup', mu);
                    resizer.classList.add('resizing');
                }};
                const mm = function(e) {{
                    const newW = w + (e.clientX - x);
                    if(newW > 100 && newW < window.innerWidth * 0.6) sidebar.style.width = `${{newW}}px`;
                }};
                const mu = function() {{
                    document.removeEventListener('mousemove', mm);
                    document.removeEventListener('mouseup', mu);
                    resizer.classList.remove('resizing');
                }};
                resizer.addEventListener('mousedown', md);
            }})();
        </script>
    </body>
    </html>
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_template)
    webbrowser.open('file://' + filepath)

# --- 3. LAUNCHER ---

def main():
    if len(sys.argv) < 2:
        print("No script provided. Running in Demo Mode...")
        df = pd.DataFrame(np.random.rand(15, 5), columns=['A','B','C','D','E']) * 100
        my_list = [10, 5, 8, 12, -3]
        mixed = [1, "A", 2]
        simple = 42.5
        txt = "Hello Var Viper"
        config = {"Settings": "Monokai"}
        show(locals())
        return
    script_path = sys.argv[1]
    if not os.path.exists(script_path):
        print(f"Error: File '{script_path}' not found.")
        return
    sys.path.append(os.path.dirname(os.path.abspath(script_path)))
    user_globals = {"__name__": "__main__", "__file__": script_path}
    print(f"--- Running {script_path} with Var Viper ---")
    try:
        with open(script_path, 'r') as f: exec(f.read(), user_globals)
    except Exception:
        traceback.print_exc()
        print("\n[Var Viper] Script failed, showing variables anyway...")

    # This pushes your script's variables into the main interactive session
    globals().update(user_globals)

    # This clears the "activate.bat" text VS Code pastes into the terminal
    # so it doesn't cause a SyntaxError when interactive mode starts.
    while msvcrt.kbhit():
        msvcrt.getch()

    show(user_globals)

if __name__ == "__main__":
    main()