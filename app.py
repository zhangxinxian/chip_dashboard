import pandas as pd
import os
import streamlit as st

# 核心配置：文件夹路径（线上部署时需改为GitHub仓库中的相对路径）
# 本地测试用：folder_path = r"C:\Users\minfa\Desktop\生产看板数据"
# 线上部署用（GitHub仓库相对路径）：
folder_path = "生产看板数据"

# 供应商-环节-字段映射
supplier_process_field_map = {
    "禾芯": {
        "BP_加工中": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY'],
        "BP_已完成": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '批次号/LOT NO', '入库日期', '芯片数量/GOOD DIE QTY'],
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY']
    },
    "日荣": {
        "ASY_加工中": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME'],
        "ASY_已完成": ['供应商', '环节', '已加工完成芯片数量', '批次号/LOT NO', '芯片名称/DEVICE NAME', '封装周码/DATE CODE'],
        "全部": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME', '已加工完成芯片数量', '封装周码/DATE CODE']
    },
    "弘润": {
        "FT_来料仓未测试": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY'],
        "FT_WIP": ['供应商', '环节', '芯片名称/DEVICE NAME', '测试订单号/FT PO', '测试类型/FT\\RT', '批次号/LOT NO', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN'],
        "FT_成品库存": ['供应商', '环节', '测试订单号/FT PO', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装周码/DATE CODE', 'BIN别/BIN', '库存数量'],
        "全部": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY', '测试订单号/FT PO', '测试类型/FT\\RT', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN', '库存数量']
    },
    "全部": {
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY', 
                 '芯片名称/DEVICE NAME', '封装订单号/ASY PO', '开始时间/START TIME', '已加工完成芯片数量', '封装周码/DATE CODE',
                 '测试订单号/FT PO', '测试类型/FT\\RT', '当前数量/WIP QTY', 'BIN别/BIN', '来料数量/IM QTY', '库存数量']
    }
}

# 供应商-环节映射
supplier_process_map = {
    "禾芯": ["BP_加工中", "BP_已完成"],
    "日荣": ["ASY_加工中", "ASY_已完成"],
    "弘润": ["FT_来料仓未测试", "FT_WIP", "FT_成品库存"],
    "全部": ["BP_加工中", "BP_已完成", "ASY_加工中", "ASY_已完成", "FT_来料仓未测试", "FT_WIP", "FT_成品库存"]
}

# ---------------------- 1. 禾芯数据提取（支持任意日期的.xlsx文件） ----------------------
def process_hexin(results):
    hexin_data = pd.DataFrame()
    # 筛选规则：文件名以数字开头 + 扩展名.xlsx
    hexin_files = [f for f in os.listdir(folder_path) 
                   if f.split('.')[0].isdigit() and f.endswith('.xlsx')]
    for file_name in hexin_files:
        file_path = os.path.join(folder_path, file_name)
        try:
            # 读取.xlsx需用openpyxl引擎
            df_wip = pd.read_excel(file_path, sheet_name="wip", header=0, engine='openpyxl')
            wip_extracted = df_wip.iloc[:, [1, 5, 7]].copy()
            wip_extracted.columns = ['批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY']
            wip_extracted['供应商'] = '禾芯'
            wip_extracted['环节'] = 'BP_加工中'

            df_fin = pd.read_excel(file_path, sheet_name="Finished Products", header=0, engine='openpyxl')
            fin_extracted = df_fin.iloc[:, [1, 2, 3, 4]].copy()
            fin_extracted.columns = ['晶圆型号/WAFER DEVICE', '入库日期', '芯片数量/GOOD DIE QTY', '批次号/LOT NO']
            fin_extracted['供应商'] = '禾芯'
            fin_extracted['环节'] = 'BP_已完成'

            hexin_data = pd.concat([hexin_data, wip_extracted, fin_extracted], ignore_index=True)
            results.append({"file": file_name, "status": "success", "msg": f"禾芯文件《{file_name}》提取成功！"})
        except Exception as e:
            results.append({"file": file_name, "status": "error", "msg": f"禾芯文件《{file_name}》提取失败：{str(e)}"})
    return hexin_data

# ---------------------- 2. 日荣数据提取（支持任意日期的ITS开头.xlsx文件） ----------------------
def process_rirong(results):
    rirong_data = pd.DataFrame()
    # 筛选规则：文件名以ITS开头 + 扩展名.xlsx
    rirong_files = [f for f in os.listdir(folder_path) 
                   if f.startswith('ITS') and f.endswith('.xlsx')]
    for file_name in rirong_files:
        file_path = os.path.join(folder_path, file_name)
        try:
            # 读取.xlsx需用openpyxl引擎
            df_wip = pd.read_excel(file_path, sheet_name="ATX WIP", header=None, engine='openpyxl')
            wip_extracted = df_wip.iloc[6:, [1, 4, 7, 12]].copy() if len(df_wip) > 6 else pd.DataFrame(columns=[1, 4, 7, 12])
            wip_extracted.columns = ['芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME']
            wip_extracted['供应商'] = '日荣'
            wip_extracted['环节'] = 'ASY_加工中'

            df_fg = pd.read_excel(file_path, sheet_name="ATX FG", header=None, engine='openpyxl')
            fg_extracted = df_fg.iloc[6:, [1, 2, 8, 13]].copy() if len(df_fg) > 6 else pd.DataFrame(columns=[1, 2, 8, 13])
            fg_extracted.columns = ['已加工完成芯片数量', '批次号/LOT NO', '芯片名称/DEVICE NAME', '封装周码/DATE CODE']
            fg_extracted['供应商'] = '日荣'
            fg_extracted['环节'] = 'ASY_已完成'

            rirong_data = pd.concat([rirong_data, wip_extracted, fg_extracted], ignore_index=True)
            results.append({"file": file_name, "status": "success", "msg": f"日荣文件《{file_name}》提取成功！（已从第7行开始读取表体）"})
        except Exception as e:
            results.append({"file": file_name, "status": "error", "msg": f"日荣文件《{file_name}》提取失败：{str(e)}"})
    
    if rirong_data.empty:
        empty_wip = pd.DataFrame(columns=supplier_process_field_map["日荣"]["ASY_加工中"])
        empty_wip['供应商'] = ['日荣']
        empty_wip['环节'] = ['ASY_加工中']
        empty_fg = pd.DataFrame(columns=supplier_process_field_map["日荣"]["ASY_已完成"])
        empty_fg['供应商'] = ['日荣']
        empty_fg['环节'] = ['ASY_已完成']
        rirong_data = pd.concat([rirong_data, empty_wip, empty_fg], ignore_index=True)
    return rirong_data

# ---------------------- 3. 弘润数据提取 ----------------------
def process_hongrun(results):
    hongrun_data = pd.DataFrame()
    hongrun_files = [f for f in os.listdir(folder_path) if 'CNEIC' in f and f.endswith('.xlsx')]
    for file_name in hongrun_files:
        file_path = os.path.join(folder_path, file_name)
        try:
            if 'WMS' in file_name:
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                extracted = df.iloc[:, [5, 7, 16]].copy()
                extracted.columns = ['芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY']
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_来料仓未测试'
            elif 'WIP' in file_name:
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                extracted = df.iloc[:, [3, 4, 7, 8, 12, 15, 16]].copy()
                extracted.columns = ['芯片名称/DEVICE NAME', '测试订单号/FT PO', '测试类型/FT\\RT', '批次号/LOT NO', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN']
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_WIP'
            elif '成品库存' in file_name:
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                extracted = df.iloc[:, [3, 5, 11, 13, 16, 17]].copy()
                extracted.columns = ['测试订单号/FT PO', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装周码/DATE CODE', 'BIN别/BIN', '库存数量']
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_成品库存'
                extracted['库存数量'] = pd.to_numeric(extracted['库存数量'], errors='coerce')
            else:
                st.warning(f"⚠️ 弘润文件《{file_name}》未匹配提取规则，跳过")
                continue

            hongrun_data = pd.concat([hongrun_data, extracted], ignore_index=True)
            results.append({"file": file_name, "status": "success", "msg": f"弘润文件《{file_name}》提取成功！"})
        except Exception as e:
            results.append({"file": file_name, "status": "error", "msg": f"弘润文件《{file_name}》提取失败：{str(e)}"})
    return hongrun_data

# ---------------------- 辅助函数：获取目标字段 ----------------------
def get_target_columns(supplier, process):
    if supplier == "全部" and process == "全部":
        return supplier_process_field_map["全部"]["全部"]
    elif supplier == "全部":
        for s in ["禾芯", "日荣", "弘润"]:
            if process in supplier_process_map[s]:
                return supplier_process_field_map[s][process]
        return supplier_process_field_map["全部"]["全部"]
    else:
        return supplier_process_field_map[supplier][process]

# ---------------------- 自定义CSS样式 ----------------------
def load_css():
    st.markdown("""
    <style>
    .bold-header th {
        font-weight: bold !important;
        background-color: #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------- 主函数：页面展示 ----------------------
def main():
    st.set_page_config(page_title="芯片生产看板", layout="wide")
    st.title("📊 芯片运营生产看板")
    
    # 加载自定义CSS
    load_css()

    if not os.path.exists(folder_path):
        st.error(f"❌ 文件夹不存在！请确认路径：{folder_path}")
        return

    results = []

    with st.spinner("正在提取数据..."):
        hexin_data = process_hexin(results)
        rirong_data = process_rirong(results)
        hongrun_data = process_hongrun(results)

    success_count = sum(1 for res in results if res["status"] == "success")
    error_count = len(results) - success_count
    button_text = "文件读取失败" if error_count > 0 else "文件读取成功"

    if 'show_file_status' not in st.session_state:
        st.session_state.show_file_status = False

    def toggle_file_status():
        st.session_state.show_file_status = not st.session_state.show_file_status

    st.button(button_text, on_click=toggle_file_status)

    if st.session_state.show_file_status:
        with st.expander("文件读取详情", expanded=True):
            for res in results:
                if res["status"] == "success":
                    st.success(res["msg"])
                else:
                    st.error(res["msg"])

    all_data = pd.concat([hexin_data, rirong_data, hongrun_data], ignore_index=True)

    all_suppliers = ['禾芯', '日荣', '弘润']
    supplier_list = ["全部"] + all_suppliers

    st.sidebar.header("🔍 筛选条件")
    supplier = st.sidebar.selectbox("选择供应商", supplier_list)
    process_list = ["全部"] + supplier_process_map[supplier]
    process = st.sidebar.selectbox("选择环节", process_list)
    
    # 添加批次号筛选
    all_lot_numbers = all_data['批次号/LOT NO'].dropna().unique().tolist()
    all_lot_numbers = sorted([lot for lot in all_lot_numbers if lot])
    lot_number_list = ["全部"] + all_lot_numbers
    selected_lot = st.sidebar.selectbox("选择批次号", lot_number_list)

    filtered_data = all_data.copy()
    if supplier != "全部":
        filtered_data = filtered_data[filtered_data['供应商'] == supplier]
    if process != "全部":
        filtered_data = filtered_data[filtered_data['环节'] == process]
    if selected_lot != "全部":
        filtered_data = filtered_data[filtered_data['批次号/LOT NO'] == selected_lot]

    target_columns = get_target_columns(supplier, process)

    if filtered_data.empty:
        filtered_data = pd.DataFrame(columns=target_columns)
    else:
        filtered_data = filtered_data.reindex(columns=target_columns).reset_index(drop=True)
        filtered_data.insert(0, "序号", range(1, len(filtered_data) + 1))

    st.subheader("📋 筛选后数据")
    st.dataframe(filtered_data, use_container_width=True, hide_index=True)

    with st.expander("查看全部数据", expanded=False):
        all_target_columns = supplier_process_field_map[supplier]["全部"] if supplier != "全部" else supplier_process_field_map["全部"]["全部"]
        if all_data.empty:
            all_display_data = pd.DataFrame(columns=all_target_columns)
        else:
            all_display_data = all_data.reindex(columns=all_target_columns).reset_index(drop=True)
            all_display_data.insert(0, "序号", range(1, len(all_display_data) + 1))
        st.dataframe(all_display_data, use_container_width=True, hide_index=True)

    if selected_lot != "全部":
        st.subheader(f"🔍 批次号追踪: {selected_lot}")
        lot_tracking_data = all_data[all_data['批次号/LOT NO'] == selected_lot].copy()
        
        if not lot_tracking_data.empty:
            lot_tracking_data = lot_tracking_data.reset_index(drop=True)
            lot_tracking_data.insert(0, "序号", range(1, len(lot_tracking_data) + 1))
            st.dataframe(lot_tracking_data, use_container_width=True, hide_index=True)
            
            st.write("**批次状态概览:**")
            for _, row in lot_tracking_data.iterrows():
                st.write(f"- {row['供应商']} | {row['环节']}")
        else:
            st.info(f"未找到批次号 {selected_lot} 的相关数据")

if __name__ == "__main__":
    main()