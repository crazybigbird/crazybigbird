import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="发动机数据可视化工具", layout="wide")
st.title("车台数据可视化")

st.markdown("""
支持三种可视化模式：
- **折线图对比**：多参数时间序列对比（支持添加计算参数：加减乘除、幂、次方等）
- **XY散点分布**：自定义 X/Y 轴，散点叠加对比
- **密度直方图**：多参数密度分布对比（叠加显示）

**所有图表均支持自定义轴范围**  
**计算参数全局生效，所有 Tab 均可用**
""")

# ==================== 自动加载 data 文件夹中的 CSV ====================
data_folder = "data"

if not os.path.exists(data_folder):
    st.error(f"未找到 '{data_folder}' 文件夹！请在项目根目录创建该文件夹，并放入 CSV 文件。")
    st.info("示例结构：\n data/发动机A.csv\n data/发动机B.csv\n ...")
    st.stop()

csv_files = [f for f in os.listdir(data_folder) if f.lower().endswith(".csv")]

if not csv_files:
    st.error(f"'{data_folder}' 文件夹为空！请放入至少一个 CSV 文件。")
    st.stop()

# 读取所有 CSV
valid_files = []
invalid_files = []

for file_name in csv_files:
    file_path = os.path.join(data_folder, file_name)
    try:
        df = pd.read_csv(
            file_path,
            sep=',',
            on_bad_lines='skip',
            encoding='utf-8-sig',
            engine='python'
        )
        if df.empty or len(df.columns) == 0:
            invalid_files.append(file_name)
        else:
            engine_name = os.path.splitext(file_name)[0]  # 文件名去掉 .csv 作为发动机名称
            valid_files.append((engine_name, df.copy()))
    except Exception as e:
        invalid_files.append(f"{file_name} ({str(e)})")

if invalid_files:
    st.warning(f"以下文件读取失败或为空，已跳过：{', '.join(invalid_files)}")

if not valid_files:
    st.error("没有有效的 CSV 文件。请检查 data 文件夹中的文件格式。")
    st.stop()

st.success(f"成功加载 {len(valid_files)} 个发动机数据：{', '.join([name for name, _ in valid_files])}")

# 收集所有列名（初始）
all_columns = set()
for _, df in valid_files:
    all_columns.update(df.columns)
columns = sorted(all_columns)

# 颜色方案
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

file_color_map = {}
color_idx = 0
for name, _ in valid_files:
    file_color_map[name] = colors[color_idx % len(colors)]
    color_idx += 1

# ==================== 计算参数功能（全局） ====================
if 'calculated_params' not in st.session_state:
    st.session_state.calculated_params = []

with st.expander("添加计算参数（全局，所有发动机都会尝试计算）", expanded=True):
    st.info("""
    表达式使用 pandas eval 语法，支持 + - * / ** () 等。
    示例：N2 * EGT / 9549（计算功率 kW）、N2 ** 2、(GET + 100) * 1.2
    """)
    col1, col2 = st.columns([2, 3])
    with col1:
        new_name = st.text_input("新参数名称（不可与现有列重名）", key="new_calc_name")
    with col2:
        new_expr = st.text_input("计算表达式（使用已有列名）", key="new_calc_expr")

    if st.button("添加计算参数"):
        if new_name and new_expr:
            if new_name in columns:
                st.warning("参数名已存在（可能是原始列），请更换")
            elif any(p["name"] == new_name for p in st.session_state.calculated_params):
                st.warning("计算参数名已存在，请更换")
            else:
                st.session_state.calculated_params.append({"name": new_name, "expr": new_expr})
                st.success(f"已添加：{new_name} = {new_expr}")
                st.rerun()
        else:
            st.warning("请填写名称和表达式")

    if st.session_state.calculated_params:
        st.write("**已添加的计算参数**（可删除）")
        for i, param in enumerate(st.session_state.calculated_params):
            col1, col2, col3 = st.columns([2, 3, 1])
            col1.write(f"**{param['name']}**")
            col2.code(param["expr"])
            if col3.button("删除", key=f"del_calc_{i}"):
                st.session_state.calculated_params.pop(i)
                st.rerun()

# 对每个发动机执行计算
for name, df in valid_files:
    for param in st.session_state.calculated_params:
        try:
            df[param["name"]] = df.eval(param["expr"])
        except Exception as e:
            st.warning(f"发动机 {name} 计算 {param['name']} 失败：{str(e)}（可能缺少所需列）")

# 重新收集列名（包含计算列）
all_columns = set()
for _, df in valid_files:
    all_columns.update(df.columns)
columns = sorted(all_columns)

# ==================== Tabs ====================
tab1, tab2, tab3 = st.tabs(["折线图对比", "XY散点分布", "密度直方图"])

# ====================== Tab 1: 折线图对比 ======================
with tab1:
    st.subheader("折线图对比（时间序列）")
    selected_line_columns = st.multiselect(
        "选择要绘制的参数列（可多选，包含计算参数）",
        columns,
        key="line_columns"
    )

    if not selected_line_columns:
        st.info("请先选择至少一个参数列进行绘图")
    else:
        with st.expander("自定义轴范围（可选）", expanded=False):
            st.info("X 轴为共享采样点范围，Y 轴可为每个参数单独设置")
            col_x1, col_x2 = st.columns(2)
            with col_x1:
                x_min_line = st.number_input("X 轴最小值（采样点）", value=None, placeholder="留空自动", key="x_min_line")
            with col_x2:
                x_max_line = st.number_input("X 轴最大值（采样点）", value=None, placeholder="留空自动", key="x_max_line")

            y_ranges_line = {}
            for col in selected_line_columns:
                st.markdown(f"**{col} 的 Y 轴范围**")
                col_y1, col_y2 = st.columns(2)
                with col_y1:
                    y_min = st.number_input(f"{col} Y 最小值", value=None, placeholder="留空自动",
                                            key=f"y_min_line_{col}")
                with col_y2:
                    y_max = st.number_input(f"{col} Y 最大值", value=None, placeholder="留空自动",
                                            key=f"y_max_line_{col}")
                if y_min is not None or y_max is not None:
                    y_ranges_line[col] = [y_min, y_max]

        fig_line = make_subplots(
            rows=len(selected_line_columns),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=[f"{col} 对比" for col in selected_line_columns]
        )

        plotted = False
        for row, column in enumerate(selected_line_columns, start=1):
            row_has_data = False
            for name, df in valid_files:
                if column not in df.columns:
                    continue
                color = file_color_map.get(name, "#808080")

                fig_line.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df[column],
                        mode='lines',
                        name=name,
                        line=dict(color=color, width=2),
                        hovertemplate="<b>%{text}</b><br>采样点: %{x}<br>" + f"{column}: " + "%{y:.4f}<extra></extra>",
                        legendgroup=name,
                        showlegend=(row == 1)
                    ),
                    row=row, col=1
                )
                fig_line.data[-1].text = [name] * len(df)
                row_has_data = True
                plotted = True

            if row_has_data:
                fig_line.update_yaxes(title_text=column, row=row, col=1)
                if column in y_ranges_line:
                    yr = y_ranges_line[column]
                    fig_line.update_yaxes(range=[yr[0] if yr[0] is not None else None,
                                                 yr[1] if yr[1] is not None else None],
                                          row=row, col=1)

        if plotted:
            fig_line.update_layout(
                title="多发动机多参数折线对比",
                hovermode="x unified",
                height=400 + 350 * len(selected_line_columns),
                legend_title="发动机",
                margin=dict(l=60, r=60, t=100, b=60)
            )
            fig_line.update_xaxes(title_text="时间步 / 采样点 (行索引)", row=len(selected_line_columns), col=1)

            if x_min_line is not None or x_max_line is not None:
                x_range = [x_min_line if x_min_line is not None else None,
                           x_max_line if x_max_line is not None else None]
                fig_line.update_xaxes(range=x_range)

            fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("选中的参数在数据中无有效值")

# ====================== Tab 2: XY散点分布 ======================
with tab2:
    st.subheader("XY散点分布")
    col_x, col_y = st.columns(2)
    with col_x:
        x_column = st.selectbox(
            "选择 X 轴列（支持计算参数）",
            ["-- 请选择 --"] + columns,
            index=0,
            key="x_scatter"
        )
    with col_y:
        y_column = st.selectbox(
            "选择 Y 轴列（支持计算参数）",
            ["-- 请选择 --"] + columns,
            index=0,
            key="y_scatter"
        )

    # 过滤占位选项
    if x_column == "-- 请选择 --":
        x_column = None
    if y_column == "-- 请选择 --":
        y_column = None

    if not x_column or not y_column:
        st.info("请分别选择 X 轴和 Y 轴参数列进行绘图")
    else:
        with st.expander("自定义轴范围（可选）", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                x_min_scatter = st.number_input("X 轴最小值", value=None, placeholder="留空自动", key="x_min_scatter")
                y_min_scatter = st.number_input("Y 轴最小值", value=None, placeholder="留空自动", key="y_min_scatter")
            with col2:
                x_max_scatter = st.number_input("X 轴最大值", value=None, placeholder="留空自动", key="x_max_scatter")
                y_max_scatter = st.number_input("Y 轴最大值", value=None, placeholder="留空自动", key="y_max_scatter")

        fig_scatter = go.Figure()
        plotted = False
        for name, df in valid_files:
            if x_column in df.columns and y_column in df.columns:
                color = file_color_map.get(name, "#808080")

                fig_scatter.add_trace(
                    go.Scatter(
                        x=df[x_column],
                        y=df[y_column],
                        mode='markers',
                        name=name,
                        marker=dict(color=color, size=6, opacity=0.6),
                        hovertemplate="<b>%{text}</b><br>" +
                                      f"{x_column}: " + "%{x:.4f}<br>" +
                                      f"{y_column}: " + "%{y:.4f}<extra></extra>"
                    )
                )
                fig_scatter.data[-1].text = [name] * len(df)
                plotted = True

        if plotted:
            fig_scatter.update_layout(
                title=f"{y_column} vs {x_column} 散点分布对比",
                xaxis_title=x_column,
                yaxis_title=y_column,
                hovermode="closest",
                height=700,
                legend_title="发动机",
                margin=dict(l=60, r=60, t=100, b=60)
            )

            if x_min_scatter is not None or x_max_scatter is not None:
                fig_scatter.update_xaxes(range=[x_min_scatter if x_min_scatter is not None else None,
                                                x_max_scatter if x_max_scatter is not None else None])
            if y_min_scatter is not None or y_max_scatter is not None:
                fig_scatter.update_yaxes(range=[y_min_scatter if y_min_scatter is not None else None,
                                                y_max_scatter if y_max_scatter is not None else None])

            fig_scatter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            fig_scatter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.warning("选中的 X/Y 列在数据中无有效值")

# ====================== Tab 3: 密度直方图 ======================
with tab3:
    st.subheader("密度直方图")
    selected_hist_columns = st.multiselect(
        "选择要绘制密度直方图的参数列（可多选，包含计算参数）",
        columns,
        key="hist_columns"
    )

    if not selected_hist_columns:
        st.info("请先选择至少一个参数列进行绘图")
    else:
        with st.expander("自定义轴范围与 bins（可选）", expanded=False):
            st.info("X 轴可为每个参数单独设置范围，Y 轴为概率密度（通常建议自动）")
            global_bins = st.number_input("全局 bins 数量（整数，留空自动）", value=None, min_value=10, step=10,
                                          key="global_bins")

            x_ranges_hist = {}
            y_ranges_hist = {}
            for col in selected_hist_columns:
                st.markdown(f"**{col} 的轴范围**")
                col_x1, col_x2 = st.columns(2)
                with col_x1:
                    x_min = st.number_input(f"{col} X 最小值", value=None, placeholder="留空自动",
                                            key=f"x_min_hist_{col}")
                with col_x2:
                    x_max = st.number_input(f"{col} X 最大值", value=None, placeholder="留空自动",
                                            key=f"x_max_hist_{col}")
                col_y1, col_y2 = st.columns(2)
                with col_y1:
                    y_min = st.number_input(f"{col} Y 最小值（密度）", value=None, placeholder="留空自动",
                                            key=f"y_min_hist_{col}")
                with col_y2:
                    y_max = st.number_input(f"{col} Y 最大值（密度）", value=None, placeholder="留空自动",
                                            key=f"y_max_hist_{col}")
                if x_min is not None or x_max is not None:
                    x_ranges_hist[col] = [x_min, x_max]
                if y_min is not None or y_max is not None:
                    y_ranges_hist[col] = [y_min, y_max]

        fig_hist = make_subplots(
            rows=len(selected_hist_columns),
            cols=1,
            vertical_spacing=0.08,
            subplot_titles=[f"{col} 密度分布" for col in selected_hist_columns]
        )

        plotted = False
        for row, column in enumerate(selected_hist_columns, start=1):
            row_has_data = False
            nbins = global_bins if global_bins else None
            for name, df in valid_files:
                if column not in df.columns:
                    continue
                color = file_color_map.get(name, "#808080")

                fig_hist.add_trace(
                    go.Histogram(
                        x=df[column].dropna(),
                        name=name,
                        histnorm='probability density',
                        opacity=0.65,
                        marker_color=color,
                        nbinsx=nbins,
                        legendgroup=name,
                        showlegend=(row == 1)
                    ),
                    row=row, col=1
                )
                row_has_data = True
                plotted = True

            if row_has_data:
                fig_hist.update_xaxes(title_text=column, row=row, col=1)
                fig_hist.update_yaxes(title_text="概率密度", row=row, col=1)

                if column in x_ranges_hist:
                    xr = x_ranges_hist[column]
                    fig_hist.update_xaxes(range=[xr[0] if xr[0] is not None else None,
                                                 xr[1] if xr[1] is not None else None], row=row, col=1)
                if column in y_ranges_hist:
                    yr = y_ranges_hist[column]
                    fig_hist.update_yaxes(range=[yr[0] if yr[0] is not None else None,
                                                 yr[1] if yr[1] is not None else None], row=row, col=1)

        if plotted:
            fig_hist.update_layout(
                title="多发动机参数密度直方图对比",
                barmode='overlay',
                hovermode="x unified",
                height=400 + 350 * len(selected_hist_columns),
                legend_title="发动机",
                margin=dict(l=60, r=60, t=100, b=60)
            )
            fig_hist.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            fig_hist.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.warning("选中的参数在数据中无有效值")

# ====================== 统计信息 ======================
if st.checkbox("显示选中参数的基本统计信息（所有 Tab 共享）"):
    all_selected = set()

    # 通过 session_state 安全获取已选择的列
    if st.session_state.get("line_columns"):
        all_selected.update(st.session_state.line_columns)
    if st.session_state.get("hist_columns"):
        all_selected.update(st.session_state.hist_columns)
    if st.session_state.get("x_scatter") and st.session_state.x_scatter != "-- 请选择 --":
        all_selected.add(st.session_state.x_scatter)
    if st.session_state.get("y_scatter") and st.session_state.y_scatter != "-- 请选择 --":
        all_selected.add(st.session_state.y_scatter)

    if all_selected:
        for column in all_selected:
            st.subheader(f"{column} 统计信息")
            stats = []
            for name, df in valid_files:
                if column in df.columns:
                    s = df[column].describe().round(4)
                    s.name = name
                    stats.append(s)
            if stats:
                df_stats = pd.concat(stats, axis=1)
                st.dataframe(df_stats)
            else:
                st.info(f"无发动机包含列 {column}")
    else:
        st.info("尚未在任何 Tab 中选择参数")
