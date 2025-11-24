import pandas as pd
import os
import streamlit as st
import hashlib
import time
import glob
import re
import json
from pathlib import Path
import shutil

# 核心配置：文件夹路径
folder_path = "生产看板数据"

# 获取稳定的用户数据文件路径
def get_users_file_path():
    home_dir = Path.home()
    app_data_dir = home_dir / ".chip_production_dashboard"
    app_data_dir.mkdir(exist_ok=True)
    users_file = app_data_dir / "users.json"
    return users_file

# 初始化用户数据（确保现有数据不被覆盖）
def initialize_users():
    users_file = get_users_file_path()
    default_users = {
        "xinxian.zhang@intchains.com": {
            "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
            "permissions": ["view", "export", "manage_users", "change_password"]
        }
    }
    if not users_file.exists():
        save_users(default_users)
        return default_users
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"加载用户数据失败，使用默认用户: {e}")
        save_users(default_users)
        return default_users

def save_users(users_data):
    try:
        users_file = get_users_file_path()
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"保存用户数据失败: {e}")
        return False

def get_users():
    return initialize_users()

def update_user_password(username, new_password_hash):
    users_data = get_users()
    if username in users_data:
        users_data[username]["password_hash"] = new_password_hash
        return save_users(users_data)
    return False

def add_new_user(username, password_hash, permissions):
    users_data = get_users()
    if username in users_data:
        return False, "用户名已存在"
    users_data[username] = {
        "password_hash": password_hash,
        "permissions": permissions
    }
    if save_users(users_data):
        return True, "用户添加成功"
    else:
        return False, "用户添加失败"

def delete_user(username):
    users_data = get_users()
    if username in users_data and username != st.session_state.username:
        del users_data[username]
        return save_users(users_data)
    return False

def get_user_permissions(username):
    users_data = get_users()
    if username in users_data:
        return users_data[username].get("permissions", [])
    return []

def check_permission(username, permission):
    permissions = get_user_permissions(username)
    return permission in permissions

def authenticate_user(username, password):
    users_data = get_users()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    if username in users_data and users_data[username]["password_hash"] == hashed_password:
        return True
    return False

# 供应商-环节-字段映射
supplier_process_field_map = {
    "禾芯": {
        "BP_加工中": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY'],
        "BP_已完成": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '批次号/LOT NO', '入库日期', '芯片数量/GOOD DIE QTY'],
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY']
    },
    "日荣": {
        "ASY_加工中": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME', 
                     '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY'],
        "ASY_已完成": ['供应商', '环节', '已加工完成芯片数量', '批次号/LOT NO', '芯片名称/DEVICE NAME', '封装周码/DATE CODE'],
        "全部": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME', 
               '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY', '已加工完成芯片数量', '封装周码/DATE CODE']
    },
    "弘润": {
        "FT_来料仓未测试": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY'],
        "FT_WIP": ['供应商', '环节', '芯片名称/DEVICE NAME', '测试订单号/FT PO', '测试类型/FT\\RT', '批次号/LOT NO', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN'],
        "FT_成品库存": ['供应商', '环节', '测试订单号/FT PO', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装周码/DATE CODE', 'BIN别/BIN', '库存数量'],
        "全部": ['供应商', '环节', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY', '测试订单号/FT PO', '测试类型/FT\\RT', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN', '库存数量']
    },
    "全部": {
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY', 
                 '芯片名称/DEVICE NAME', '封装订单号/ASY PO', '开始时间/START TIME', '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY',
                 '已加工完成芯片数量', '封装周码/DATE CODE', '测试订单号/FT PO', '测试类型/FT\\RT', 'BIN别/BIN', '来料数量/IM QTY', '库存数量']
    }
}

supplier_process_map = {
    "禾芯": ["BP_加工中", "BP_已完成"],
    "日荣": ["ASY_加工中", "ASY_已完成"],
    "弘润": ["FT_来料仓未测试", "FT_WIP", "FT_成品库存"],
    "全部": ["BP_加工中", "BP_已完成", "ASY_加工中", "ASY_已完成", "FT_来料仓未测试", "FT_WIP", "FT_成品库存"]
}

# ---------------------- 登录页面 ----------------------
def login_page():
    st.set_page_config(
        page_title="芯片生产看板 - 登录", 
        layout="centered",
        page_icon="intchains_logo.png"  # 浏览器标签图标（若需保留可继续使用，无需修改）
    )
    st.title("🔐 芯片生产看板 - 用户登录")
    with st.form("login_form"):
        username = st.text_input("用户名", placeholder="请输入用户名")
        password = st.text_input("密码", type="password", placeholder="请输入密码")
        submit_button = st.form_submit_button("登录")
        if submit_button:
            if authenticate_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.current_page = "dashboard"
                st.success(f"欢迎回来，{username}！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("用户名或密码错误！")

# ---------------------- 个人账户页面 ----------------------
def personal_account_page():
    st.subheader("👤 个人账户")
    st.write(f"**用户名:** {st.session_state.username}")
    st.write("---")
    st.write("### 修改密码")
    with st.form("change_password_form"):
        current_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_password = st.text_input("确认新密码", type="password")
        submit_button = st.form_submit_button("修改密码")
        if submit_button:
            current_hashed = hashlib.sha256(current_password.encode()).hexdigest()
            users_data = get_users()
            if current_hashed != users_data.get(st.session_state.username, {}).get("password_hash", ""):
                st.error("当前密码错误！")
                return
            if new_password != confirm_password:
                st.error("新密码和确认密码不匹配！")
                return
            if len(new_password) < 6:
                st.error("密码长度至少6位！")
                return
            new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
            if update_user_password(st.session_state.username, new_hashed):
                st.success("密码修改成功！")
            else:
                st.error("密码修改失败！")

# ---------------------- 用户管理页面 ----------------------
def user_management_page():
    st.subheader("👥 用户管理")
    users_data = get_users()
    st.write("### 当前用户列表")
    user_list = []
    for username, user_info in users_data.items():
        user_list.append({
            '用户名': username,
            '权限': ', '.join(user_info.get("permissions", [])),
            '状态': '在线' if username == st.session_state.username else '离线'
        })
    user_df = pd.DataFrame(user_list)
    st.dataframe(user_df, use_container_width=True)
    st.write("### 添加新用户")
    with st.form("add_user_form"):
        new_username = st.text_input("新用户名")
        new_password = st.text_input("密码", type="password")
        user_role = st.selectbox("用户角色", ["viewer", "operator", "admin"])
        submit_button = st.form_submit_button("添加用户")
        if submit_button:
            if len(new_username) == 0:
                st.error("用户名不能为空！")
            elif new_username in users_data:
                st.error("用户名已存在！")
            elif len(new_password) < 6:
                st.error("密码长度至少6位！")
            else:
                role_permissions = {
                    "viewer": ["view"],
                    "operator": ["view", "export", "change_password"],
                    "admin": ["view", "export", "manage_users", "change_password"]
                }
                new_hashed = hashlib.sha256(new_password.encode()).hexdigest()
                success, message = add_new_user(new_username, new_hashed, role_permissions[user_role])
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    st.write("### 删除用户")
    delete_username = st.selectbox("选择要删除的用户", 
                                  [user for user in users_data.keys() if user != st.session_state.username])
    if st.button("删除用户", type="secondary"):
        if delete_user(delete_username):
            st.success(f"用户 {delete_username} 已删除")
            st.rerun()
        else:
            st.error("删除用户失败")

# ---------------------- 生产看板页面 ----------------------
def dashboard_page():
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
    st.sidebar.header("🔍 筛选条件")
    all_suppliers = ['禾芯', '日荣', '弘润']
    supplier_list = ["全部"] + all_suppliers
    supplier = st.sidebar.selectbox("选择供应商", supplier_list)
    process_list = ["全部"] + supplier_process_map[supplier]
    process = st.sidebar.selectbox("选择环节", process_list)
    all_lot_numbers = all_data['批次号/LOT NO'].dropna().unique().tolist()
    all_lot_numbers = sorted([lot for lot in all_lot_numbers if lot])
    lot_number_list = ["全部"] + all_lot_numbers
    selected_lot = st.sidebar.selectbox("选择批次号", lot_number_list)
    if supplier == "日荣" and process == "ASY_加工中":
        all_processes = all_data[all_data['供应商'] == '日荣']['当前环节'].dropna().unique().tolist()
        all_processes = sorted([p for p in all_processes if p])
        process_list = ["全部"] + all_processes
        selected_process = st.sidebar.selectbox("选择当前环节", process_list)
    else:
        selected_process = "全部"
    filtered_data = all_data.copy()
    if supplier != "全部":
        filtered_data = filtered_data[filtered_data['供应商'] == supplier]
    if process != "全部":
        filtered_data = filtered_data[filtered_data['环节'] == process]
    if selected_lot != "全部":
        filtered_data = filtered_data[filtered_data['批次号/LOT NO'] == selected_lot]
    if selected_process != "全部" and supplier == "日荣" and process == "ASY_加工中":
        filtered_data = filtered_data[filtered_data['当前环节'] == selected_process]
    target_columns = get_target_columns(supplier, process)
    if filtered_data.empty:
        filtered_data = pd.DataFrame(columns=target_columns)
    else:
        filtered_data = filtered_data.reindex(columns=target_columns).reset_index(drop=True)
        filtered_data.insert(0, "序号", range(1, len(filtered_data) + 1))
    st.subheader("📋 筛选后数据")
    st.dataframe(filtered_data, use_container_width=True, hide_index=True)
    if check_permission(st.session_state.username, "export"):
        if not filtered_data.empty:
            csv_data = filtered_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 导出CSV",
                data=csv_data,
                file_name=f"芯片生产数据_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    if supplier == "日荣" and process == "ASY_加工中":
        if not filtered_data.empty and '当前环节' in filtered_data.columns:
            st.subheader("📊 日荣ASY环节统计")
            process_stats = filtered_data.groupby('当前环节')['当前数量/WIP QTY'].sum().reset_index()
            process_stats.columns = ['环节', '总数量']
            process_stats = process_stats.sort_values('总数量', ascending=False)
            st.dataframe(process_stats, use_container_width=True, hide_index=True)
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
                status_info = f"- {row['供应商']} | {row['环节']}"
                if row['供应商'] == '日荣' and row['环节'] == 'ASY_加工中' and '当前环节' in row:
                    status_info += f" | 当前环节: {row['当前环节']} | 数量: {row['当前数量/WIP QTY']}"
                st.write(status_info)
        else:
            st.info(f"未找到批次号 {selected_lot} 的相关数据")

# ---------------------- 数据提取函数 ----------------------
def process_hexin(results):
    hexin_data = pd.DataFrame()
    hexin_files = [f for f in os.listdir(folder_path) 
                   if f.split('.')[0].isdigit() and f.endswith('.xlsx')]
    for file_name in hexin_files:
        file_path = os.path.join(folder_path, file_name)
        try:
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

def process_rirong(results):
    rirong_data = pd.DataFrame()
    rirong_files = [f for f in os.listdir(folder_path) 
                   if f.startswith('ITS') and f.endswith('.xlsx')]
    for file_name in rirong_files:
        file_path = os.path.join(folder_path, file_name)
        try:
            df_wip = pd.read_excel(file_path, sheet_name="ATX WIP", header=None, engine='openpyxl')
            process_columns = list(range(13, 23))
            process_names = df_wip.iloc[5, process_columns].tolist()
            wip_extracted = df_wip.iloc[6:, [1, 4, 7, 9, 12]].copy()
            wip_extracted.columns = ['芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', 
                                    '下单数量/ORDER QTY', '开始时间/START TIME']
            process_data = df_wip.iloc[6:, process_columns].copy()
            current_processes = []
            current_qtys = []
            for idx, row in process_data.iterrows():
                non_zero_cols = []
                for i, val in enumerate(row):
                    try:
                        if pd.notna(val) and float(val) != 0:
                            non_zero_cols.append((i, val))
                    except (ValueError, TypeError):
                        continue
                if non_zero_cols:
                    col_idx, qty = non_zero_cols[0]
                    current_processes.append(process_names[col_idx])
                    current_qtys.append(qty)
                else:
                    current_processes.append("")
                    current_qtys.append(0)
            wip_extracted['当前环节'] = current_processes
            wip_extracted['当前数量/WIP QTY'] = current_qtys
            wip_extracted['供应商'] = '日荣'
            wip_extracted['环节'] = 'ASY_加工中'
            df_fg = pd.read_excel(file_path, sheet_name="ATX FG", header=None, engine='openpyxl')
            fg_extracted = df_fg.iloc[6:, [1, 2, 8, 13]].copy() if len(df_fg) > 6 else pd.DataFrame(columns=[1, 2, 8, 13])
            fg_extracted.columns = ['已加工完成芯片数量', '批次号/LOT NO', '芯片名称/DEVICE NAME', '封装周码/DATE CODE']
            fg_extracted['供应商'] = '日荣'
            fg_extracted['环节'] = 'ASY_已完成'
            rirong_data = pd.concat([rirong_data, wip_extracted, fg_extracted], ignore_index=True)
            results.append({"file": file_name, "status": "success", "msg": f"日荣文件《{file_name}》提取成功！（已增加环节信息）"})
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

def load_css():
    st.markdown("""
    <style>
    .bold-header th {
        font-weight: bold !important;
        background-color: #f0f2f6;
    }
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        border: 1px solid #ddd;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------- 主应用 ----------------------
def main_app():
    st.set_page_config(
        page_title="芯片生产看板", 
        layout="wide",
        page_icon="intchains_logo.png"  # 浏览器标签图标（若需保留可继续使用，无需修改）
    )
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    # 仅保留文字标题，移除图标
    st.title("芯片运营生产看板")
    col3 = st.columns([1])[0]
    with col3:
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.current_page = "dashboard"
            st.rerun()
    st.write(f"👤 当前用户: **{st.session_state.username}**")
    load_css()
    st.sidebar.header("📱 导航")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("📊 生产看板", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with col2:
        if st.button("👤 个人账户", use_container_width=True):
            st.session_state.current_page = "personal_account"
            st.rerun()
    if check_permission(st.session_state.username, "manage_users"):
        if st.sidebar.button("👥 用户管理", use_container_width=True):
            st.session_state.current_page = "user_management"
            st.rerun()
    if st.session_state.current_page == "dashboard":
        dashboard_page()
    elif st.session_state.current_page == "personal_account":
        personal_account_page()
    elif st.session_state.current_page == "user_management":
        user_management_page()

# ---------------------- 主函数 ----------------------
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
