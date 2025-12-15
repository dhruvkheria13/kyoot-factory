import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- Configuration & Setup ---
st.set_page_config(page_title="Factory Inventory", layout="wide", page_icon="🏭")
TRANS_FILE = "inventory_transactions.csv"
MASTERS_FILE = "inventory_masters.csv"

# --- Session State for Navigation ---
if 'page' not in st.session_state:
    st.session_state.page = "1. Closing Stock (Dashboard)"

def navigate_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- Data Management Functions ---
def load_transactions():
    if not os.path.exists(TRANS_FILE):
        columns = [
            "Date", "Type", "ID", "Party_Name", "Item_Name", "Quantity", "Unit", 
            "Batch_ID", "Ball_Mill_ID", "Status", "Notes"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_csv(TRANS_FILE, index=False)
        return df
    return pd.read_csv(TRANS_FILE)

def load_masters():
    if not os.path.exists(MASTERS_FILE):
        df = pd.DataFrame(columns=["Type", "Name"])
        df.to_csv(MASTERS_FILE, index=False)
        return df
    return pd.read_csv(MASTERS_FILE)

def save_data(df, filename):
    df.to_csv(filename, index=False)

def get_next_id(df, type_prefix):
    df['ID'] = df['ID'].astype(str)
    type_rows = df[df['ID'].str.startswith(type_prefix, na=False)]
    if type_rows.empty:
        return f"{type_prefix}-001"
    else:
        return f"{type_prefix}-{len(type_rows)+1:03d}"

def update_database_from_editor(original_df, edited_subset):
    df_indexed = original_df.set_index("ID")
    subset_indexed = edited_subset.set_index("ID")
    df_indexed.update(subset_indexed)
    return df_indexed.reset_index()

# --- Main App Interface ---
def main():
    st.title("🏭 Factory Inventory System")
    
    # Load Data
    df = load_transactions()
    
    # --- SAFETY FIX: Handle Date Errors Automatically ---
    # This line prevents the crash by fixing bad date formats
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
    
    # If any dates were corrupted (NaT), remove those rows to keep app running
    if df['Date'].isna().any():
        df = df.dropna(subset=['Date'])
    
    masters = load_masters()

    # Get Lists from Masters
    raw_materials = masters[masters['Type'] == 'Material']['Name'].unique().tolist()
    grades = masters[masters['Type'] == 'Grade']['Name'].unique().tolist()
    suppliers = masters[masters['Type'] == 'Supplier']['Name'].unique().tolist()
    customers = masters[masters['Type'] == 'Customer']['Name'].unique().tolist()
    mills = ["Ball Mill 1", "Ball Mill 2", "Ball Mill 3", "Ball Mill 4", "Ball Mill 5"]

    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title("Navigation")
    menu_options = [
        "1. Closing Stock (Dashboard)",
        "2. Batch Entry",
        "3. Ball Mill",
        "4. Sales",
        "5. Purchase",
        "6. Party Ledgers",
        "7. View Data",
        "8. Master Data"
    ]
    
    try:
        current_index = menu_options.index(st.session_state.page)
    except:
        current_index = 0
        
    choice = st.sidebar.radio("Go to", menu_options, index=current_index)
    st.session_state.page = choice

    # --- SIDEBAR BACKUP ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Backup Data")
    csv_trans = df.to_csv(index=False).encode('utf-8')
    csv_masters = masters.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button("Download Transactions", csv_trans, 'backup_transactions.csv', 'text/csv')
    st.sidebar.download_button("Download Masters", csv_masters, 'backup_masters.csv', 'text/csv')

    # ==========================================
    # 1. CLOSING STOCK (DASHBOARD)
    # ==========================================
    if choice == "1. Closing Stock (Dashboard)":
        st.header("📊 Closing Stock")
        col_d1, col_d2 = st.columns([1, 3])
        view_date = col_d1.date_input("Stock as of:", datetime.now())
        
        filtered_stock_df = df[df['Date'] <= view_date]
        stock_df = filtered_stock_df.groupby("Item_Name")[['Quantity']].sum().reset_index()
        stock_df.columns = ["Item", "Stock"]
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Raw Materials")
            st.dataframe(stock_df[stock_df['Item'].isin(raw_materials)], hide_index=True, use_container_width=True)
        with c2:
            st.subheader("Finished Grades & Batches")
            st.dataframe(stock_df[~stock_df['Item'].isin(raw_materials)], hide_index=True, use_container_width=True)

    # ==========================================
    # 2. BATCH ENTRY
    # ==========================================
    elif choice == "2. Batch Entry":
        st.header("⚗️ Make Batch (UF Lumps)")
        
        if not raw_materials:
            st.warning("⚠️ No Raw Materials found.")
            if st.button("➕ Add Raw Materials in Master"): navigate_to("8. Master Data")
        else:
            col_top1, col_top2 = st.columns(2)
            b_date = col_top1.date_input("Entry Date", datetime.now())
            batch_id = col_top2.text_input("Batch ID", get_next_id(df, "BAT"))
            
            st.subheader("1. New Entry")
            with st.expander("📝 Open Entry Form", expanded=True):
                st.write("Enter quantity for items used:")
                input_data = [{"Item": mat, "Quantity": 0.0} for mat in raw_materials]
                input_df = pd.DataFrame(input_data)
                edited_input = st.data_editor(input_df, num_rows="fixed", use_container_width=True, height=200, key="batch_input")
                
                batches_made = st.number_input("No. of Batches Made", min_value=0.0, step=0.1, format="%.2f")
                
                if st.button("Save Batch"):
                    if batches_made > 0:
                        new_entries = []
                        for index, row in edited_input.iterrows():
                            if row['Quantity'] > 0:
                                new_entries.append({
                                    "Date": b_date, "Type": "Batch_Consumption", "ID": f"{batch_id}-IN-{index}",
                                    "Item_Name": row['Item'], "Quantity": -row['Quantity'], 
                                    "Unit": "Kg/L", "Batch_ID": batch_id
                                })
                        new_entries.append({
                            "Date": b_date, "Type": "Batch_Production", "ID": f"{batch_id}-OUT",
                            "Item_Name": "UF Lumps (Batches)", "Quantity": batches_made, 
                            "Unit": "Batches", "Batch_ID": batch_id
                        })
                        df = pd.concat([df, pd.DataFrame(new_entries)], ignore_index=True)
                        save_data(df, TRANS_FILE)
                        st.success("Batch Recorded!")
                        st.rerun()

            st.markdown("---")
            st.subheader(f"📅 Log for {b_date}")
            mask = (df['Date'] == b_date) & (df['Type'].str.contains("Batch"))
            daily_df = df[mask]
            
            if not daily_df.empty:
                st.info("💡 Edit entries below.")
                edited_daily = st.data_editor(daily_df, use_container_width=True, num_rows="dynamic", key="batch_editor")
                if st.button("Save Updates (Batch Log)"):
                    df = update_database_from_editor(df, edited_daily)
                    save_data(df, TRANS_FILE)
                    st.success("Changes Saved!")
                    st.rerun()
            else:
                st.caption("No batches recorded on this date.")

    # ==========================================
    # 3. BALL MILL
    # ==========================================
    elif choice == "3. Ball Mill":
        st.header("⚙️ Ball Mill Management")
        m_date = st.date_input("Entry Date", datetime.now())
        
        tab1, tab2 = st.tabs(["🆕 Start New Process", "🔄 Update/Finish Active"])
        
        with tab1:
            with st.form("mill_start"):
                mill_select = st.selectbox("Select Mill", mills)
                batches_in = st.number_input("No. of UF Batches to Load", min_value=0.0, step=0.5)
                if st.form_submit_button("Start Milling"):
                    ts = str(int(datetime.now().timestamp()))
                    entry = {
                        "Date": m_date, "Type": "Mill_Start", "ID": f"MIL-{ts}",
                        "Ball_Mill_ID": mill_select, "Item_Name": "UF Lumps (Batches)",
                        "Quantity": -batches_in, "Unit": "Batches", "Status": "In Progress"
                    }
                    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                    save_data(df, TRANS_FILE)
                    st.success(f"{mill_select} Started!")
                    st.rerun()

        with tab2:
            active_mill = st.selectbox("Select Active Mill", mills, key="act_mill")
            action_type = st.radio("Action", ["Add Material", "Finish & Produce Bags"])
            
            if action_type == "Add Material":
                if not raw_materials:
                     st.warning("No materials defined.")
                else:
                    with st.form("add_mat"):
                        mat_item = st.selectbox("Material", raw_materials)
                        mat_qty = st.number_input("Quantity (Kg)", min_value=0.0, step=0.1)
                        if st.form_submit_button("Add to Mill"):
                            ts = str(int(datetime.now().timestamp()))
                            entry = {
                                "Date": m_date, "Type": "Mill_Consumption", "ID": f"ADD-{ts}",
                                "Ball_Mill_ID": active_mill, "Item_Name": mat_item,
                                "Quantity": -mat_qty, "Unit": "Kg"
                            }
                            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                            st.success("Added!")
                            st.rerun()

            elif action_type == "Finish & Produce Bags":
                if not grades:
                     st.warning("No Grades defined.")
                else:
                    with st.form("finish_mill"):
                        out_grade = st.selectbox("Produced Grade", grades)
                        bags = st.number_input("No. of Bags Produced", min_value=1)
                        if st.form_submit_button("Finish Process"):
                            ts = str(int(datetime.now().timestamp()))
                            entry = {
                                "Date": m_date, "Type": "Mill_Production", "ID": f"FIN-{ts}",
                                "Ball_Mill_ID": active_mill, "Item_Name": out_grade,
                                "Quantity": bags, "Unit": "Bags", "Status": "Completed"
                            }
                            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                            st.success(f"Production Recorded!")
                            st.rerun()

        st.markdown("---")
        st.subheader(f"📅 Log for {m_date}")
        mask = (df['Date'] == m_date) & (df['Type'].str.contains("Mill"))
        daily_df = df[mask]
        
        if not daily_df.empty:
            st.info("💡 Edit mill entries below.")
            edited_daily = st.data_editor(daily_df, use_container_width=True, num_rows="dynamic", key="mill_editor")
            if st.button("Save Updates (Mill Log)"):
                df = update_database_from_editor(df, edited_daily)
                save_data(df, TRANS_FILE)
                st.success("Changes Saved!")
                st.rerun()
        else:
            st.caption("No ball mill activity on this date.")

    # ==========================================
    # 4. SALES
    # ==========================================
    elif choice == "4. Sales":
        st.header("🚚 Sales Entry")
        col_chk1, col_chk2 = st.columns(2)
        if not customers: col_chk1.warning("⚠️ No Customers.")
        if not grades: col_chk2.warning("⚠️ No Grades.")
            
        s_date = st.date_input("Sales Date", datetime.now())
        
        if customers and grades:
            with st.expander("📝 New Sale", expanded=True):
                with st.form("sales_entry"):
                    cust = st.selectbox("Customer", customers)
                    grade_sold = st.selectbox("Grade", grades)
                    bags_sold = st.number_input("Bags Sold", min_value=1)
                    
                    if st.form_submit_button("Record Sale"):
                        new_id = get_next_id(df, "SAL")
                        entry = {
                            "Date": s_date, "Type": "Sales", "ID": new_id,
                            "Party_Name": cust, "Item_Name": grade_sold,
                            "Quantity": -bags_sold, "Unit": "Bags"
                        }
                        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                        save_data(df, TRANS_FILE)
                        st.success("Sale Recorded!")
                        st.rerun()

            st.markdown("---")
            st.subheader(f"📅 Log for {s_date}")
            mask = (df['Date'] == s_date) & (df['Type'] == "Sales")
            daily_df = df[mask]
            
            if not daily_df.empty:
                st.info("💡 Edit sales below.")
                edited_daily = st.data_editor(daily_df, use_container_width=True, num_rows="dynamic", key="sales_editor")
                if st.button("Save Updates (Sales Log)"):
                    df = update_database_from_editor(df, edited_daily)
                    save_data(df, TRANS_FILE)
                    st.success("Changes Saved!")
                    st.rerun()
            else:
                st.caption("No sales on this date.")

    # ==========================================
    # 5. PURCHASE
    # ==========================================
    elif choice == "5. Purchase":
        st.header("🛒 Purchase Entry")
        col_chk1, col_chk2 = st.columns(2)
        if not suppliers: col_chk1.warning("⚠️ No Suppliers.")
        if not raw_materials: col_chk2.warning("⚠️ No Items.")

        p_date = st.date_input("Purchase Date", datetime.now())

        if suppliers and raw_materials:
            with st.expander("📝 New Purchase", expanded=True):
                with st.form("purchase_form"):
                    supplier = st.selectbox("Supplier", suppliers)
                    col3, col4, col5 = st.columns(3)
                    item = col3.selectbox("Item", raw_materials)
                    qty = col4.number_input("Quantity", min_value=0.0, step=0.1)
                    unit = col5.selectbox("Unit", ["Kg", "Litres", "Pieces"])
                    notes = st.text_input("Invoice No / Notes")
                    
                    if st.form_submit_button("Save Purchase"):
                        new_id = get_next_id(df, "PUR")
                        entry = {
                            "Date": p_date, "Type": "Purchase", "ID": new_id, 
                            "Party_Name": supplier, "Item_Name": item, 
                            "Quantity": qty, "Unit": unit, "Status": "In Stock", "Notes": notes
                        }
                        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                        save_data(df, TRANS_FILE)
                        st.success(f"Saved! ID: {new_id}")
                        st.rerun()

            st.markdown("---")
            st.subheader(f"📅 Log for {p_date}")
            mask = (df['Date'] == p_date) & (df['Type'] == "Purchase")
            daily_df = df[mask]
            
            if not daily_df.empty:
                st.info("💡 Edit purchases below.")
                edited_daily = st.data_editor(daily_df, use_container_width=True, num_rows="dynamic", key="pur_editor")
                if st.button("Save Updates (Purchase Log)"):
                    df = update_database_from_editor(df, edited_daily)
                    save_data(df, TRANS_FILE)
                    st.success("Changes Saved!")
                    st.rerun()
            else:
                st.caption("No purchases on this date.")

    # ==========================================
    # 6. PARTY LEDGERS
    # ==========================================
    elif choice == "6. Party Ledgers":
        st.header("📒 Supplier & Customer Ledgers")
        
        type_filter = st.radio("Select Type", ["Supplier", "Customer"], horizontal=True)
        party_list = suppliers if type_filter == "Supplier" else customers
        selected_party = st.selectbox(f"Select {type_filter}", ["All"] + party_list)
        
        if selected_party != "All":
            ledger_data = df[df['Party_Name'] == selected_party]
        else:
            ledger_data = df[df['Party_Name'].isin(party_list)]
        st.dataframe(ledger_data, use_container_width=True)

    # ==========================================
    # 7. VIEW DATA
    # ==========================================
    elif choice == "7. View Data":
        st.header("💾 Master Log")
        st.info("Full database view.")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="main_editor")
        if st.button("Save Database Changes"):
            save_data(edited_df, TRANS_FILE)
            st.success("Saved!")

    # ==========================================
    # 8. MASTER DATA
    # ==========================================
    elif choice == "8. Master Data":
        st.header("🛠️ Master Data")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Add New")
            with st.form("add_master"):
                m_type = st.selectbox("Type", ["Material", "Grade", "Supplier", "Customer"])
                m_name = st.text_input("Name")
                
                opening_stock = 0.0
                if m_type in ["Material", "Grade"]:
                    st.markdown("---")
                    opening_stock = st.number_input("Opening Quantity", min_value=0.0, step=0.1)
                
                if st.form_submit_button("Add"):
                    if m_name and m_name not in masters[masters['Type'] == m_type]['Name'].values:
                        new_row = {"Type": m_type, "Name": m_name}
                        masters = pd.concat([masters, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(masters, MASTERS_FILE)
                        
                        if opening_stock > 0:
                            unit = "Bags" if m_type == "Grade" else "Kg"
                            op_entry = {
                                "Date": datetime.now().date(), "Type": "Opening Stock", "ID": get_next_id(df, "OPN"),
                                "Item_Name": m_name, "Quantity": opening_stock, "Unit": unit, 
                                "Status": "Stock In", "Notes": "Initial Balance"
                            }
                            df = pd.concat([df, pd.DataFrame([op_entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                        st.success(f"Added {m_name}")
                        st.rerun()
                    else:
                        st.error("Invalid or Duplicate Name")

        with c2:
            st.subheader("List")
            search = st.text_input("🔍 Search")
            if search:
                mask = masters['Name'].str.lower().str.startswith(search.lower())
                st.dataframe(masters[mask], use_container_width=True)
            else:
                st.dataframe(masters, use_container_width=True)

if __name__ == "__main__":
    main()
