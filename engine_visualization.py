import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="发动机数据可视化工具", layout="wide")
st.title("车台数据可视化")

st.markdown("""
上传多个 CSV 文件（支持多选），支持三种可视化模式：
- **折线图对比**：多参数时间序列对比（每个参数独立子图）
- **XY散点分布**：自定义 X/Y 轴，查看多文件散点叠加对比
- **密度直方图**：多参数密度分布对比（每个参数独立子图，叠加显示）

**所有图表均支持自定义轴范围（可选）**  
**鼠标悬停均可查看详细信息**
""")

# 支持多文件上传
uploaded_files = st.file_uploader(
    "上传 CSV 文件（支持多选）",
    type=["csv"],
    accept_multiple_files=True
)

if uploaded_files:
    # 读取所有有效文件
    valid_files = []  # (uploaded_file, df)
    invalid_files = []

    for uploaded_file in uploaded_files:
        try:
            df = pd.read_csv(
                uploaded_file,
                sep=',',
                on_bad_lines='skip',
                encoding='utf-8-sig',
                engine='python'
            )
            if df.empty or len(df.columns) == 0:
                invalid_files.append(uploaded_file.name)
            else:
                valid_files.append((uploaded_file, df))
        except pd.errors.EmptyDataError:
            invalid_files.append(uploaded_file.name)
        except Exception as e:
            invalid_files.append(f"{uploaded_file.name} ({str(e)})")

    if invalid_files:
        st.warning(f"以下文件读取失败或为空，已跳过：{', '.join(invalid_files)}")

    if not valid_files:
        st.error("没有有效的 CSV 文件可以读取。请检查上传的文件是否包含数据和列。")
        st.stop()

    # 收集所有文件中出现的唯一列名
    all_columns = set()
    for _, df in valid_files:
        all_columns.update(df.columns)
    columns = sorted(all_columns)

    if not columns:
        st.error("上传的文件中没有发现任何列。请检查 CSV 文件格式。")
        st.stop()

    # 颜色方案（每个文件固定一种颜色）
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
              "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]

    file_color_map = {}
    color_idx = 0
    for uploaded_file, _ in valid_files:
        filename = uploaded_file.name.split('.')[0]
        if filename not in file_color_map:
            file_color_map[filename] = colors[color_idx % len(colors)]
            color_idx += 1

    # Tabs 分页
    tab1, tab2, tab3 = st.tabs(["折线图对比", "XY散点分布", "密度直方图"])

    # ====================== Tab 1: 折线图对比 ======================
    with tab1:
        st.subheader("折线图对比（时间序列）")
        selected_line_columns = st.multiselect(
            "选择要绘制的参数列（可多选）",
            columns,
            default=columns[:3] if len(columns) >= 3 else columns,
            key="line_columns"
        )

        if selected_line_columns:
            # 自定义轴范围
            with st.expander("自定义轴范围（可选）", expanded=False):
                st.info("X 轴为共享采样点范围，Y 轴可为每个参数单独设置")
                col_x1, col_x2 = st.columns(2)
                with col_x1:
                    x_min_line = st.number_input("X 轴最小值（采样点）", value=None, placeholder="留空自动",
                                                 key="x_min_line")
                with col_x2:
                    x_max_line = st.number_input("X 轴最大值（采样点）", value=None, placeholder="留空自动",
                                                 key="x_max_line")

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
                for uploaded_file, df in valid_files:
                    if column not in df.columns:
                        continue
                    filename = uploaded_file.name.split('.')[0]
                    color = file_color_map.get(filename, "#808080")

                    fig_line.add_trace(
                        go.Scatter(
                            x=df.index,
                            y=df[column],
                            mode='lines',
                            name=filename,
                            line=dict(color=color, width=2),
                            hovertemplate="<b>%{text}</b><br>采样点: %{x}<br>" + f"{column}: " + "%{y:.4f}<extra></extra>",
                            legendgroup=filename,
                            showlegend=(row == 1)
                        ),
                        row=row, col=1
                    )
                    fig_line.data[-1].text = [filename] * len(df)
                    row_has_data = True
                    plotted = True

                if row_has_data:
                    fig_line.update_yaxes(title_text=column, row=row, col=1)
                    # 应用 Y 范围
                    if column in y_ranges_line:
                        y_range = y_ranges_line[column]
                        if y_range[0] is not None and y_range[1] is not None:
                            fig_line.update_yaxes(range=y_range, row=row, col=1)
                        elif y_range[0] is not None:
                            fig_line.update_yaxes(rangemin=y_range[0], row=row, col=1)
                        elif y_range[1] is not None:
                            fig_line.update_yaxes(rangemax=y_range[1], row=row, col=1)

            if plotted:
                fig_line.update_layout(
                    title="多文件多参数折线对比",
                    hovermode="x unified",
                    height=400 + 350 * len(selected_line_columns),
                    legend_title="文件",
                    margin=dict(l=60, r=60, t=100, b=60)
                )
                fig_line.update_xaxes(title_text="时间步 / 采样点 (行索引)", row=len(selected_line_columns), col=1)

                # 应用共享 X 范围（只在最底部应用，所有共享）
                if x_min_line is not None or x_max_line is not None:
                    x_range = [x_min_line if x_min_line is not None else fig_line.data[0].x.min(),
                               x_max_line if x_max_line is not None else fig_line.data[0].x.max()]
                    if x_min_line is None:
                        x_range[0] = None
                    if x_max_line is None:
                        x_range[1] = None
                    fig_line.update_xaxes(range=x_range)

                fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.warning("选中的参数在文件中无数据")

    # ====================== Tab 2: XY散点分布 ======================
    with tab2:
        st.subheader("XY散点分布")
        col_x, col_y = st.columns(2)
        with col_x:
            x_column = st.selectbox("选择 X 轴列", columns, key="x_scatter")
        with col_y:
            y_column = st.selectbox("选择 Y 轴列", columns, key="y_scatter")

        if x_column and y_column:
            # 自定义轴范围
            with st.expander("自定义轴范围（可选）", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    x_min_scatter = st.number_input("X 轴最小值", value=None, placeholder="留空自动",
                                                    key="x_min_scatter")
                    y_min_scatter = st.number_input("Y 轴最小值", value=None, placeholder="留空自动",
                                                    key="y_min_scatter")
                with col2:
                    x_max_scatter = st.number_input("X 轴最大值", value=None, placeholder="留空自动",
                                                    key="x_max_scatter")
                    y_max_scatter = st.number_input("Y 轴最大值", value=None, placeholder="留空自动",
                                                    key="y_max_scatter")

            fig_scatter = go.Figure()
            plotted = False
            for uploaded_file, df in valid_files:
                if x_column in df.columns and y_column in df.columns:
                    filename = uploaded_file.name.split('.')[0]
                    color = file_color_map.get(filename, "#808080")

                    fig_scatter.add_trace(
                        go.Scatter(
                            x=df[x_column],
                            y=df[y_column],
                            mode='markers',
                            name=filename,
                            marker=dict(color=color, size=6, opacity=0.6),
                            hovertemplate=
                            "<b>%{text}</b><br>" +
                            f"{x_column}: " + "%{x:.4f}<br>" +
                            f"{y_column}: " + "%{y:.4f}<extra></extra>"
                        )
                    )
                    fig_scatter.data[-1].text = [filename] * len(df)
                    plotted = True

            if plotted:
                fig_scatter.update_layout(
                    title=f"{y_column} vs {x_column} 散点分布对比",
                    xaxis_title=x_column,
                    yaxis_title=y_column,
                    hovermode="closest",
                    height=700,
                    legend_title="文件",
                    margin=dict(l=60, r=60, t=100, b=60)
                )

                # 应用自定义范围
                if x_min_scatter is not None or x_max_scatter is not None:
                    fig_scatter.update_xaxes(range=[x_min_scatter,
                                                    x_max_scatter] if x_min_scatter is not None and x_max_scatter is not None else None)
                if y_min_scatter is not None or y_max_scatter is not None:
                    fig_scatter.update_yaxes(range=[y_min_scatter,
                                                    y_max_scatter] if y_min_scatter is not None and y_max_scatter is not None else None)

                fig_scatter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                fig_scatter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                st.plotly_chart(fig_scatter, use_container_width=True)
            else:
                st.warning("选中的 X/Y 列在文件中无数据")

    # ====================== Tab 3: 密度直方图 ======================
    with tab3:
        st.subheader("密度直方图")
        selected_hist_columns = st.multiselect(
            "选择要绘制密度直方图的参数列（可多选）",
            columns,
            default=columns[:3] if len(columns) >= 3 else columns,
            key="hist_columns"
        )

        if selected_hist_columns:
            # 自定义轴范围 + bins
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
                for uploaded_file, df in valid_files:
                    if column not in df.columns:
                        continue
                    filename = uploaded_file.name.split('.')[0]
                    color = file_color_map.get(filename, "#808080")

                    fig_hist.add_trace(
                        go.Histogram(
                            x=df[column].dropna(),
                            name=filename,
                            histnorm='probability density',
                            opacity=0.65,
                            marker_color=color,
                            nbinsx=nbins,
                            legendgroup=filename,
                            showlegend=(row == 1)
                        ),
                        row=row, col=1
                    )
                    row_has_data = True
                    plotted = True

                if row_has_data:
                    fig_hist.update_xaxes(title_text=column, row=row, col=1)
                    fig_hist.update_yaxes(title_text="概率密度", row=row, col=1)

                    # 应用范围
                    if column in x_ranges_hist:
                        xr = x_ranges_hist[column]
                        fig_hist.update_xaxes(range=xr, row=row, col=1)
                    if column in y_ranges_hist:
                        yr = y_ranges_hist[column]
                        fig_hist.update_yaxes(range=yr, row=row, col=1)

            if plotted:
                fig_hist.update_layout(
                    title="多文件参数密度直方图对比",
                    barmode='overlay',
                    hovermode="x unified",
                    height=400 + 350 * len(selected_hist_columns),
                    legend_title="文件",
                    margin=dict(l=60, r=60, t=100, b=60)
                )
                fig_hist.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                fig_hist.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.warning("选中的参数在文件中无数据")

    # ====================== 统计信息 ======================
    if st.checkbox("显示选中参数的基本统计信息（所有 Tab 共享）"):
        all_selected = set()
        if 'selected_line_columns' in locals():
            all_selected.update(selected_line_columns)
        if 'selected_hist_columns' in locals():
            all_selected.update(selected_hist_columns)
        if 'x_column' in locals() and 'y_column' in locals():
            all_selected.update([x_column, y_column])

        if all_selected:
            for column in all_selected:
                st.subheader(f"{column} 统计信息")
                stats = []
                for uploaded_file, df in valid_files:
                    if column in df.columns:
                        s = df[column].describe().round(4)
                        s.name = uploaded_file.name.split('.')[0]
                        stats.append(s)
                if stats:
                    st.dataframe(pd.concat(stats, axis=1))
                else:
                    st.info(f"无文件包含列 {column}")

else:
    st.info("请上传至少一个 CSV 文件开始可视化")


