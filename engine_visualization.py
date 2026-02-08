import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

# ==================== 页面配置 ====================
st.set_page_config(page_title="发动机数据可视化工具", layout="wide")
st.title("车台数据可视化")

st.markdown("""
支持三种可视化模式：
- **折线图对比**：多参数时间序列对比（支持添加计算参数）
- **XY散点分布**：自定义 X/Y 轴，**支持按索引范围（时间步）筛选数据**
- **密度直方图**：多参数密度分布对比

**所有图表均支持自定义轴范围** **计算参数全局生效，所有 Tab 均可用**
""")

# ==================== 文件上传功能 ====================
st.sidebar.header("上传数据文件")
uploaded_files = st.sidebar.file_uploader(
    "上传CSV文件（可多选）",
    type=["csv"],
    accept_multiple_files=True,
    help="支持上传多个CSV文件进行比较分析"
)

# 初始化session_state用于存储上传的文件
if 'valid_files' not in st.session_state:
    st.session_state.valid_files = []

# 当上传文件变化时更新数据
current_file_names = [f.name for f in uploaded_files] if uploaded_files else []
stored_file_names = [name for name, _ in st.session_state.valid_files]

# 如果没有上传文件，显示提示信息
if not uploaded_files:
    st.info("👈 请从左侧边栏上传CSV文件开始分析")
    st.session_state.valid_files = []  # 清空缓存
    st.stop()

# 检查文件列表是否发生变化
if set(current_file_names) != set(stored_file_names):
    st.session_state.valid_files = []
    invalid_files = []

    for uploaded_file in uploaded_files:
        try:
            # 读取CSV文件
            content = uploaded_file.read()

            # 尝试不同的编码
            try:
                content_str = content.decode('utf-8-sig')
            except:
                content_str = content.decode('gbk')

            df = pd.read_csv(
                io.StringIO(content_str),
                sep=',',
                on_bad_lines='skip',
                engine='python'
            )

            if df.empty or len(df.columns) == 0:
                invalid_files.append(f"{uploaded_file.name} (文件为空或格式错误)")
            else:
                # 使用文件名作为发动机名称
                engine_name = uploaded_file.name.replace('.csv', '').replace('.CSV', '')
                st.session_state.valid_files.append((engine_name, df.copy()))

        except Exception as e:
            invalid_files.append(f"{uploaded_file.name} ({str(e)})")

    if invalid_files:
        st.sidebar.warning(f"以下文件读取失败：{', '.join(invalid_files)}")

valid_files = st.session_state.valid_files

if not valid_files:
    st.error("没有有效的CSV文件。请检查文件格式。")
    st.stop()

st.sidebar.success(f"已加载 {len(valid_files)} 个文件")

# 在侧边栏显示已加载的文件列表
with st.sidebar.expander("已加载的文件详情", expanded=False):
    for name, df in valid_files:
        st.write(f"**{name}**")
        st.caption(f"Rows: {df.shape[0]}, Cols: {df.shape[1]}")
        st.divider()

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

with st.expander("添加计算参数（全局，所有发动机都会尝试计算）", expanded=False):
    st.info("表达式使用 pandas eval 语法。示例：N2 * EGT / 9549")
    col1, col2 = st.columns([2, 3])
    with col1:
        new_name = st.text_input("新参数名称", key="new_calc_name")
    with col2:
        new_expr = st.text_input("计算表达式", key="new_calc_expr")

    if st.button("添加计算参数"):
        if new_name and new_expr:
            if new_name in columns:
                st.warning("参数名已存在，请更换")
            else:
                st.session_state.calculated_params.append({"name": new_name, "expr": new_expr})
                st.success(f"已添加：{new_name}")
                st.rerun()

    if st.session_state.calculated_params:
        st.markdown("---")
        for i, param in enumerate(st.session_state.calculated_params):
            c1, c2, c3 = st.columns([2, 3, 1])
            c1.write(f"**{param['name']}**")
            c2.code(param["expr"])
            if c3.button("删除", key=f"del_calc_{i}"):
                st.session_state.calculated_params.pop(i)
                st.rerun()

# 对每个发动机执行计算
for name, df in valid_files:
    for param in st.session_state.calculated_params:
        try:
            if param["name"] not in df.columns:
                df[param["name"]] = df.eval(param["expr"])
        except:
            pass  # 忽略计算错误

# 重新收集列名
all_columns = set()
for _, df in valid_files:
    all_columns.update(df.columns)
columns = sorted(all_columns)

# ==================== Tabs ====================
tab1, tab2, tab3 = st.tabs(["折线图对比", "XY散点分布", "密度直方图"])

# ====================== Tab 1: 折线图对比 ======================
with tab1:
    st.subheader("折线图对比（时间序列）")
    selected_line_columns = st.multiselect("选择参数（Y轴）", columns, key="line_columns")

    if selected_line_columns:
        with st.expander("自定义轴范围", expanded=False):
            cx1, cx2 = st.columns(2)
            x_min_line = cx1.number_input("X轴 Min (点)", value=None, key="lx1")
            x_max_line = cx2.number_input("X轴 Max (点)", value=None, key="lx2")

            y_ranges_line = {}
            for col in selected_line_columns:
                st.markdown(f"**{col} Y轴**")
                cy1, cy2 = st.columns(2)
                ymin = cy1.number_input(f"Min", value=None, key=f"lym_{col}")
                ymax = cy2.number_input(f"Max", value=None, key=f"lyM_{col}")
                if ymin is not None or ymax is not None:
                    y_ranges_line[col] = [ymin, ymax]

        fig_line = make_subplots(rows=len(selected_line_columns), cols=1, shared_xaxes=True,
                                 vertical_spacing=0.08, subplot_titles=selected_line_columns)

        plotted = False
        for row, column in enumerate(selected_line_columns, start=1):
            for name, df in valid_files:
                if column in df.columns:
                    fig_line.add_trace(go.Scatter(
                        x=df.index, y=df[column], mode='lines', name=name,
                        line=dict(color=file_color_map.get(name), width=1.5),
                        legendgroup=name, showlegend=(row == 1)
                    ), row=row, col=1)
                    plotted = True

            if column in y_ranges_line:
                fig_line.update_yaxes(range=y_ranges_line[column], row=row, col=1)

        if plotted:
            fig_line.update_layout(height=300 * len(selected_line_columns), hovermode="x unified")
            if x_min_line is not None or x_max_line is not None:
                fig_line.update_xaxes(range=[x_min_line, x_max_line])
            st.plotly_chart(fig_line, use_container_width=True)

# ====================== Tab 2: XY散点分布 (已更新) ======================
with tab2:
    st.subheader("XY散点分布 (支持索引筛选)")
    col_x, col_y = st.columns(2)
    x_column = col_x.selectbox("X 轴", ["-- 请选择 --"] + columns, key="xs")
    y_column = col_y.selectbox("Y 轴", ["-- 请选择 --"] + columns, key="ys")

    if x_column != "-- 请选择 --" and y_column != "-- 请选择 --":
        # --- 索引范围筛选 ---
        st.divider()
        st.markdown("**数据范围筛选 (基于行索引)**")
        max_len = max([len(df) for _, df in valid_files]) if valid_files else 100

        idx_range = st.slider(
            "选择采样点范围", 0, max_len, (0, max_len),
            help="仅显示在此索引范围内的数据点"
        )
        start_idx, end_idx = idx_range
        st.caption(f"当前显示范围: {start_idx} - {end_idx}")

        with st.expander("自定义数值轴范围", expanded=False):
            c1, c2 = st.columns(2)
            xmin = c1.number_input("X Min", value=None, key="sxm")
            xmax = c2.number_input("X Max", value=None, key="sxM")
            ymin = c1.number_input("Y Min", value=None, key="sym")
            ymax = c2.number_input("Y Max", value=None, key="syM")

        fig_scatter = go.Figure()
        plotted = False

        for name, df in valid_files:
            if x_column in df.columns and y_column in df.columns:
                # 切片逻辑
                local_s = min(start_idx, len(df))
                local_e = min(end_idx, len(df))
                if local_s >= local_e: continue

                df_slice = df.iloc[local_s:local_e]

                fig_scatter.add_trace(go.Scatter(
                    x=df_slice[x_column], y=df_slice[y_column],
                    mode='markers', name=name,
                    marker=dict(color=file_color_map.get(name), size=5, opacity=0.6),
                    customdata=df_slice.index,
                    hovertemplate=f"<b>{name}</b><br>Idx: %{{customdata}}<br>X: %{{x:.2f}}<br>Y: %{{y:.2f}}<extra></extra>"
                ))
                plotted = True

        if plotted:
            fig_scatter.update_layout(
                title=f"{y_column} vs {x_column} (Index: {start_idx}-{end_idx})",
                xaxis_title=x_column, yaxis_title=y_column,
                height=600, hovermode="closest"
            )
            if xmin is not None or xmax is not None: fig_scatter.update_xaxes(range=[xmin, xmax])
            if ymin is not None or ymax is not None: fig_scatter.update_yaxes(range=[ymin, ymax])
            st.plotly_chart(fig_scatter, use_container_width=True)

# ====================== Tab 3: 密度直方图 ======================
with tab3:
    st.subheader("密度直方图")
    hist_cols = st.multiselect("选择参数", columns, key="hc")

    if hist_cols:
        fig_hist = make_subplots(rows=len(hist_cols), cols=1, subplot_titles=hist_cols)
        plotted = False
        for row, col in enumerate(hist_cols, start=1):
            for name, df in valid_files:
                if col in df.columns:
                    fig_hist.add_trace(go.Histogram(
                        x=df[col], name=name, histnorm='probability density',
                        opacity=0.6, marker_color=file_color_map.get(name),
                        legendgroup=name, showlegend=(row == 1)
                    ), row=row, col=1)
                    plotted = True

        if plotted:
            fig_hist.update_layout(barmode='overlay', height=300 * len(hist_cols))
            st.plotly_chart(fig_hist, use_container_width=True)

# ====================== 统计信息 ======================
if st.checkbox("显示统计信息"):
    sel_cols = set(st.session_state.get("line_columns", []) + st.session_state.get("hc", []))
    if st.session_state.get("xs") != "-- 请选择 --": sel_cols.add(st.session_state.xs)
    if st.session_state.get("ys") != "-- 请选择 --": sel_cols.add(st.session_state.ys)

    if sel_cols:
        for col in sel_cols:
            if col:
                st.markdown(f"**{col}**")
                stats = [df[col].describe().rename(name) for name, df in valid_files if col in df.columns]
                if stats: st.dataframe(pd.concat(stats, axis=1).round(4))
