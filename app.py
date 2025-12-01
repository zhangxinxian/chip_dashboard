import pandas as pd
import os
import streamlit as st
import hashlib
import time
import json
from pathlib import Path
import shutil
import plotly.express as px
import plotly.graph_objects as go

# 核心配置：文件夹路径
folder_path = "生产看板数据"

# 获取稳定的用户数据文件路径
def get_users_file_path():
    home_dir = Path.home()
    app_data_dir = home_dir / ".chip_production_dashboard"
    app_data_dir.mkdir(exist_ok=True)
    users_file = app_data_dir / "users.json"
    return users_file

# 迁移旧用户数据（如果存在）
def migrate_old_users_data():
    old_users_file = Path(__file__).parent.absolute() / "users.json"
    new_users_file = get_users_file_path()
    if not new_users_file.exists() and old_users_file.exists():
        try:
            shutil.copy2(old_users_file, new_users_file)
            print(f"已从 {old_users_file} 迁移用户数据到 {new_users_file}")
        except Exception as e:
            print(f"用户数据迁移失败: {e}")

# 初始化用户数据
def initialize_users():
    migrate_old_users_data()
    users_file = get_users_file_path()
    default_users = {
        "xinxian.zhang@intchains.com": {
            "password_hash": hashlib.sha256("123456".encode()).hexdigest(),
            "permissions": ["view", "export", "manage_users", "change_password"]
        },
        "min.fang@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        },
        "weiwei.zhang@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        },
        "zhihao.zhang@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        },
        "jing.pan@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        },
        "miron.jin@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        },
        "xianghui.zeng@intchains.com": {
            "password_hash": hashlib.sha256("intchains".encode()).hexdigest(),
            "permissions": ["view"]
        }
    }
    if not users_file.exists():
        save_users(default_users)
        return default_users
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            existing_users = json.load(f)
            for username, user_info in default_users.items():
                if username not in existing_users:
                    existing_users[username] = user_info
                else:
                    existing_users[username]["permissions"] = user_info["permissions"]
            save_users(existing_users)
            return existing_users
    except Exception as e:
        print(f"加载用户数据失败: {e}")
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

# 用户权限配置
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
        "BP_加工中": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '晶圆数量/WAFER QTY'],
        "BP_已完成": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '批次号/LOT NO', '入库日期', '芯片数量/GOOD DIE QTY'],
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY']
    },
    "日荣": {
        "ASY_加工中": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME', 
                     '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY'],
        "ASY_已完成": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '已加工完成芯片数量', '批次号/LOT NO', '封装周码/DATE CODE'],
        "全部": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装订单号/ASY PO', '开始时间/START TIME', 
               '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY', '已加工完成芯片数量', '封装周码/DATE CODE']
    },
    "弘润": {
        "FT_来料仓未测试": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY'],
        "FT_WIP": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '测试订单号/FT PO', '测试类型/FT\\RT', '批次号/LOT NO', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN'],
        "FT_成品库存": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '测试订单号/FT PO', '批次号/LOT NO', '封装周码/DATE CODE', 'BIN别/BIN', '库存数量'],
        "全部": ['供应商', '环节', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '批次号/LOT NO', '来料数量/IM QTY', '测试订单号/FT PO', '测试类型/FT\\RT', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN', '库存数量']
    },
    "全部": {
        "全部": ['供应商', '环节', '批次号/LOT NO', '晶圆型号/WAFER DEVICE', '芯片名称/DEVICE NAME', '晶圆数量/WAFER QTY', '入库日期', '芯片数量/GOOD DIE QTY', 
                 '封装订单号/ASY PO', '开始时间/START TIME', '下单数量/ORDER QTY', '当前环节', '当前数量/WIP QTY',
                 '已加工完成芯片数量', '封装周码/DATE CODE', '测试订单号/FT PO', '测试类型/FT\\RT', 'BIN别/BIN', '来料数量/IM QTY', '库存数量']
    }
}

# 供应商-环节映射
supplier_process_map = {
    "禾芯": ["BP_加工中", "BP_已完成"],
    "日荣": ["ASY_加工中", "ASY_已完成"],
    "弘润": ["FT_来料仓未测试", "FT_WIP", "FT_成品库存"],
    "全部": ["BP_加工中", "BP_已完成", "ASY_加工中", "ASY_已完成", "FT_来料仓未测试", "FT_WIP", "FT_成品库存"]
}

# ---------------------- 登录页面 ----------------------
def login_page():
    st.set_page_config(
        page_title="INTCHAINS - 聪链 - 登录", 
        layout="centered",
        page_icon="intchains_logo.png"
    )
    st.markdown("<h1 style='text-align: center;'>INTCHAINS</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>—— 聪链 ——</h3>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>用户登录</h2>", unsafe_allow_html=True)
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

# ---------------------- 数据处理函数 ----------------------
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
            wip_extracted['芯片名称/DEVICE NAME'] = None
            wip_extracted['数量'] = pd.to_numeric(wip_extracted['晶圆数量/WAFER QTY'], errors='coerce')

            df_fin = pd.read_excel(file_path, sheet_name="Finished Products", header=0, engine='openpyxl')
            fin_extracted = df_fin.iloc[:, [1, 2, 3, 4]].copy()
            fin_extracted.columns = ['晶圆型号/WAFER DEVICE', '入库日期', '芯片数量/GOOD DIE QTY', '批次号/LOT NO']
            fin_extracted['供应商'] = '禾芯'
            fin_extracted['环节'] = 'BP_已完成'
            fin_extracted['芯片名称/DEVICE NAME'] = None
            fin_extracted['数量'] = pd.to_numeric(fin_extracted['芯片数量/GOOD DIE QTY'], errors='coerce')

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
            wip_extracted['晶圆型号/WAFER DEVICE'] = None
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
                    current_qtys.append(float(qty) if pd.notna(qty) else 0)
                else:
                    current_processes.append("")
                    current_qtys.append(0)
            wip_extracted['当前环节'] = current_processes
            wip_extracted['当前数量/WIP QTY'] = current_qtys
            wip_extracted['供应商'] = '日荣'
            wip_extracted['环节'] = 'ASY_加工中'
            wip_extracted['数量'] = pd.to_numeric(wip_extracted['当前数量/WIP QTY'], errors='coerce')

            df_fg = pd.read_excel(file_path, sheet_name="ATX FG", header=None, engine='openpyxl')
            fg_extracted = df_fg.iloc[:, [1, 2, 8, 13]].copy() if len(df_fg) > 6 else pd.DataFrame(columns=[1, 2, 8, 13])
            fg_extracted.columns = ['已加工完成芯片数量', '批次号/LOT NO', '芯片名称/DEVICE NAME', '封装周码/DATE CODE']
            fg_extracted['晶圆型号/WAFER DEVICE'] = None
            fg_extracted['供应商'] = '日荣'
            fg_extracted['环节'] = 'ASY_已完成'
            fg_extracted['数量'] = pd.to_numeric(fg_extracted['已加工完成芯片数量'], errors='coerce')

            rirong_data = pd.concat([rirong_data, wip_extracted, fg_extracted], ignore_index=True)
            results.append({"file": file_name, "status": "success", "msg": f"日荣文件《{file_name}》提取成功！"})
        except Exception as e:
            results.append({"file": file_name, "status": "error", "msg": f"日荣文件《{file_name}》提取失败：{str(e)}"})
    if rirong_data.empty:
        empty_cols = supplier_process_field_map["日荣"]["全部"]
        empty_wip = pd.DataFrame(columns=empty_cols)
        empty_wip['供应商'] = ['日荣']
        empty_wip['环节'] = ['ASY_加工中']
        empty_fg = pd.DataFrame(columns=empty_cols)
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
                extracted['晶圆型号/WAFER DEVICE'] = None
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_来料仓未测试'
                extracted['数量'] = pd.to_numeric(extracted['来料数量/IM QTY'], errors='coerce')
            elif 'WIP' in file_name:
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                extracted = df.iloc[:, [3, 4, 7, 8, 12, 15, 16]].copy()
                extracted.columns = ['芯片名称/DEVICE NAME', '测试订单号/FT PO', '测试类型/FT\\RT', '批次号/LOT NO', '封装周码/DATE CODE', '当前数量/WIP QTY', 'BIN别/BIN']
                extracted['晶圆型号/WAFER DEVICE'] = None
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_WIP'
                extracted['数量'] = pd.to_numeric(extracted['当前数量/WIP QTY'], errors='coerce')
            elif '成品库存' in file_name:
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                extracted = df.iloc[:, [3, 5, 11, 13, 16, 17]].copy()
                extracted.columns = ['测试订单号/FT PO', '芯片名称/DEVICE NAME', '批次号/LOT NO', '封装周码/DATE CODE', 'BIN别/BIN', '库存数量']
                extracted['晶圆型号/WAFER DEVICE'] = None
                extracted['供应商'] = '弘润'
                extracted['环节'] = 'FT_成品库存'
                extracted['数量'] = pd.to_numeric(extracted['库存数量'], errors='coerce')
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

# ---------------------- 数据图模块 ----------------------
def render_charts(all_data):
    # 读取侧边栏的筛选条件
    supplier = st.session_state.get("table_supplier_select", "全部")
    process = st.session_state.get("table_process_select", "全部")
    selected_wafer = st.session_state.get("table_wafer_select", ["全部"])
    selected_device = st.session_state.get("table_device_select", ["全部"])
    
    # 过滤有效数据
    chart_data = all_data.dropna(subset=['数量'])
    chart_data = chart_data[chart_data['数量'] > 0]
    
    # 应用筛选条件
    if supplier != "全部":
        chart_data = chart_data[chart_data['供应商'] == supplier]
    if process != "全部":
        chart_data = chart_data[chart_data['环节'] == process]
    if selected_wafer != ["全部"] and len(selected_wafer) > 0:
        chart_data = chart_data[chart_data['晶圆型号/WAFER DEVICE'].isin(selected_wafer)]
    if selected_device != ["全部"] and len(selected_device) > 0:
        chart_data = chart_data[chart_data['芯片名称/DEVICE NAME'].isin(selected_device)]
    
    if chart_data.empty:
        st.info("暂无符合筛选条件的数据图数据")
        return
    
    # 供应商-低饱和度颜色映射
    supplier_color_map = {
        "弘润": ["#6c9dc6"],  # 低饱和蓝色（单颜色，避免多色干扰）
        "日荣": ["#f5b88e"],  # 低饱和橙色
        "禾芯": ["#8dc68d"]   # 低饱和绿色
    }
    
    # 计算汇总数据
    summary_data = chart_data.groupby(['供应商', '环节'])['数量'].sum().reset_index()
    
    # 确定展示的供应商列表
    display_suppliers = summary_data['供应商'].unique().tolist() if supplier == "全部" else [supplier]
    
    # 分供应商展示柱状图
    cols = st.columns(len(display_suppliers))
    for idx, s in enumerate(display_suppliers):
        with cols[idx]:
            s_data = summary_data[summary_data['供应商'] == s]
            if s_data.empty:
                st.info(f"{s}暂无数据")
                continue
            
            # 选择对应供应商的低饱和颜色
            color_seq = supplier_color_map.get(s, ["#cccccc"])
            
            # 创建柱状图
            fig = px.bar(
                s_data,
                x='环节',
                y='数量',
                title=f'{s}',
                color='环节',
                color_discrete_sequence=color_seq,
                text='数量',
                height=450  # 增大图表高度，避免文字截断
            )
            
            # 图表样式配置：字体放大+黑色、去掉X轴文字、调整柱体宽度
            fig.update_layout(
                xaxis_title="",
                yaxis_title='数量',
                title_x=0.5,
                title_font=dict(size=16, color='black'),  # 标题字体
                font=dict(size=14, color='black'),  # 全局字体
                xaxis=dict(
                    tickfont=dict(size=12, color='black'),  # X轴刻度字体
                    tickangle=0  # 刻度水平显示，避免重叠
                ),
                yaxis=dict(
                    tickfont=dict(size=12, color='black'),  # Y轴刻度字体
                    autorange=True
                ),
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=40),  # 调整边距，确保文字显示
                plot_bgcolor='white'  # 背景白色，提升对比度
            )
            
            # 柱体调整：宽度减半、边框样式
            fig.update_traces(
                width=0.5,  # 柱体宽度设为0.5（原默认1，即减半）
                textposition='outside',
                texttemplate='%{text:.0f}',
                textfont=dict(size=12, color='black'),  # 数据标签字体
                marker=dict(
                    line=dict(color='black', width=1)  # 柱体边框
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)

# ---------------------- 数据表模块 ----------------------
def render_data_tables(all_data):
    st.subheader("📋 数据表展示")
    
    # 侧边栏筛选条件
    st.sidebar.header("🔍 数据筛选")
    
    # 供应商筛选
    all_suppliers = ['禾芯', '日荣', '弘润']
    supplier_list = ["全部"] + all_suppliers
    supplier = st.sidebar.selectbox(
        "选择供应商",
        supplier_list,
        key="table_supplier_select"
    )
    
    # 环节筛选
    process_list = ["全部"] + supplier_process_map[supplier]
    process = st.sidebar.selectbox(
        "选择环节",
        process_list,
        key="table_process_select"
    )
    
    # SERVICE (DEVICE层面)
    st.sidebar.markdown("### SERVICE (DEVICE层面)")
    wafer_types = sorted(all_data['晶圆型号/WAFER DEVICE'].dropna().unique().tolist())
    selected_wafer = st.sidebar.multiselect(
        "选择晶圆型号",
        ["全部"] + wafer_types,
        default=["全部"],
        key="table_wafer_select"
    )
    
    device_names = sorted(all_data['芯片名称/DEVICE NAME'].dropna().unique().tolist())
    selected_device = st.sidebar.multiselect(
        "选择芯片名称",
        ["全部"] + device_names,
        default=["全部"],
        key="table_device_select"
    )
    
    # 批次号筛选
    all_lot_numbers = all_data['批次号/LOT NO'].dropna().unique().tolist()
    all_lot_numbers = sorted([lot for lot in all_lot_numbers if lot])
    lot_number_list = ["全部"] + all_lot_numbers
    selected_lots = st.sidebar.multiselect(
        "选择批次号（可多选）",
        lot_number_list,
        default=["全部"],
        key="table_lot_select"
    )
    
    # 日荣特定环节筛选
    if supplier == "日荣" and process == "ASY_加工中":
        all_processes = all_data[all_data['供应商'] == '日荣']['当前环节'].dropna().unique().tolist()
        all_processes = sorted([p for p in all_processes if p])
        process_list = ["全部"] + all_processes
        selected_process = st.sidebar.selectbox(
            "选择当前环节",
            process_list,
            key="table_rirong_process_select"
        )
    else:
        selected_process = "全部"

    # 数据筛选逻辑
    filtered_data = all_data.copy()
    if supplier != "全部":
        filtered_data = filtered_data[filtered_data['供应商'] == supplier]
    if process != "全部":
        filtered_data = filtered_data[filtered_data['环节'] == process]
    if selected_wafer != ["全部"] and len(selected_wafer) > 0:
        filtered_data = filtered_data[filtered_data['晶圆型号/WAFER DEVICE'].isin(selected_wafer)]
    if selected_device != ["全部"] and len(selected_device) > 0:
        filtered_data = filtered_data[filtered_data['芯片名称/DEVICE NAME'].isin(selected_device)]
    if "全部" not in selected_lots and selected_lots:
        filtered_data = filtered_data[filtered_data['批次号/LOT NO'].isin(selected_lots)]
    if selected_process != "全部" and supplier == "日荣" and process == "ASY_加工中":
        filtered_data = filtered_data[filtered_data['当前环节'] == selected_process]

    # 准备展示数据
    target_columns = get_target_columns(supplier, process)
    if filtered_data.empty:
        display_data = pd.DataFrame(columns=target_columns)
    else:
        display_data = filtered_data.reindex(columns=target_columns).reset_index(drop=True)
        display_data.insert(0, "序号", range(1, len(display_data) + 1))
    
    # 显示筛选后数据
    st.write("### 筛选后数据")
    st.dataframe(display_data, use_container_width=True, hide_index=True)
    
    # 导出功能
    if check_permission(st.session_state.username, "export") and not display_data.empty:
        csv_data = display_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出筛选数据CSV",
            data=csv_data,
            file_name=f"生产数据_筛选_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # 日荣环节统计
    if supplier == "日荣" and process == "ASY_加工中" and not filtered_data.empty and '当前环节' in filtered_data.columns:
        st.write("### 日荣环节统计")
        process_stats = filtered_data.groupby('当前环节')['当前数量/WIP QTY'].sum().reset_index()
        process_stats.columns = ['环节', '总数量']
        process_stats = process_stats.sort_values('总数量', ascending=False)
        st.dataframe(process_stats, use_container_width=True, hide_index=True)
    
    # 查看全部数据
    with st.expander("查看全部原始数据", expanded=False):
        all_target_columns = supplier_process_field_map[supplier]["全部"] if supplier != "全部" else supplier_process_field_map["全部"]["全部"]
        all_display_data = all_data.reindex(columns=all_target_columns).reset_index(drop=True)
        all_display_data.insert(0, "序号", range(1, len(all_display_data) + 1))
        st.dataframe(all_display_data, use_container_width=True, hide_index=True)
        
        if check_permission(st.session_state.username, "export"):
            all_csv_data = all_display_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 导出全部数据CSV",
                data=all_csv_data,
                file_name=f"生产数据_全部_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    # 批次号追踪
    if "全部" not in selected_lots and selected_lots:
        st.write(f"### 批次号追踪: {', '.join(selected_lots)}")
        lot_tracking_data = all_data[all_data['批次号/LOT NO'].isin(selected_lots)].copy()
        if not lot_tracking_data.empty:
            lot_tracking_data = lot_tracking_data.reset_index(drop=True)
            lot_tracking_data.insert(0, "序号", range(1, len(lot_tracking_data) + 1))
            st.dataframe(lot_tracking_data, use_container_width=True, hide_index=True)
        else:
            st.info(f"未找到批次号 {', '.join(selected_lots)} 的相关数据")

# ---------------------- 主看板页面 ----------------------
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
    
    # 模块命名
    tab1, tab2 = st.tabs(["📈 数据图", "📋 数据表"])
    
    with tab1:
        render_charts(all_data)
    
    with tab2:
        render_data_tables(all_data)

# ---------------------- 主应用 ----------------------
def main_app():
    st.set_page_config(
        page_title="INTCHAINS - 聪链 - 生产看板", 
        layout="wide",
        page_icon="intchains_logo.png"
    )
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "dashboard"
    st.markdown("<h1 style='text-align: center;'>INTCHAINS</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 30px;'>—— 聪链 —— 生产看板</h3>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([3, 3, 1])
    with col3:
        if st.button("🚪 退出登录"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.current_page = "dashboard"
            st.rerun()
    st.write(f"👤 当前用户: **{st.session_state.username}**")
    
    # 加载自定义CSS：彻底移除筛选条件的所有额外颜色
    st.markdown("""
    <style>
    .intchains-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .intchains-subtitle {
        text-align: center;
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
        margin-bottom: 30px;
    }
    /* 筛选条件（MultiSelect）无任何额外颜色 */
    .stMultiSelect {
        background-color: white !important;
    }
    .stMultiSelect div[data-baseweb="tag"] {
        background-color: transparent !important;
        color: black !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 4px;
    }
    .stMultiSelect div[data-baseweb="tag"]:hover {
        background-color: #f5f5f5 !important;
    }
    .stMultiSelect div[data-baseweb="tag"] span[data-baseweb="tag-close"] {
        color: black !important;
    }
    /* 下拉框无额外颜色 */
    .stSelectbox {
        background-color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 侧边栏导航
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
    
    # 页面路由
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
