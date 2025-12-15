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
        # STARTED BLANK
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

# --- Main App Interface ---
def main():
    st.title("🏭 Factory Inventory System")
    
    # Load Data
    df = load_transactions()
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
    
    # Navigation Logic
    try:
        current_index = menu_options.index(st.session_state.page)
    except:
        current_index = 0
        
    choice = st.sidebar.radio("Go to", menu_options, index=current_index)
    st.session_state.page = choice

    # --- SIDEBAR BACKUP BUTTONS ---
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
        stock_df = df.groupby("Item_Name")[['Quantity']].sum().reset_index()
        stock_df.columns = ["Item", "Current Stock"]
        
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
            if st.button("➕ Add Raw Materials in Master"):
                navigate_to("8. Master Data")
        else:
            col_top1, col_top2 = st.columns(2)
            b_date = col_top1.date_input("Date", datetime.now())
            batch_id = col_top2.text_input("Batch ID", get_next_id(df, "BAT"))
            
            st.subheader("Ingredients Input")
            
            input_data = []
            for mat in raw_materials:
                input_data.append({"Item": mat, "Quantity": 0.0})
            
            input_df = pd.DataFrame(input_data)
            
            st.write("Enter quantity for items used in this batch:")
            edited_df = st.data_editor(input_df, num_rows="fixed", use_container_width=True, height=300)
            
            total_input_weight = edited_df['Quantity'].sum()
            st.metric("Total Input Weight (Kg/L)", f"{total_input_weight:.2f}")

            st.subheader("Production Output")
            batches_made = st.number_input("No. of Batches Made (Decimals allowed)", min_value=0.0, step=0.1, format="%.2f")
            
            if st.button("Save Batch Production"):
                if batches_made > 0:
                    new_entries = []
                    for index, row in edited_df.iterrows():
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
                    st.success("Batch Recorded Successfully!")

    # ==========================================
    # 3. BALL MILL
    # ==========================================
    elif choice == "3. Ball Mill":
        st.header("⚙️ Ball Mill Management")
        
        tab1, tab2 = st.tabs(["🆕 Start New Process", "🔄 Update/Finish Active"])
        
        with tab1:
            st.subheader("Load Ball Mill")
            with st.form("mill_start"):
                m_date = st.date_input("Date", datetime.now())
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

        with tab2:
            st.subheader("Update Running Mill")
            active_mill = st.selectbox("Select Active Mill", mills, key="act_mill")
            
            action_type = st.radio("Action", ["Add Material (Zinc/Masala)", "Finish & Produce Bags"])
            
            if action_type == "Add Material (Zinc/Masala)":
                if not raw_materials:
                     st.warning("No materials defined.")
                     if st.button("➕ Add Materials"): navigate_to("8. Master Data")
                else:
                    with st.form("add_mat"):
                        mat_item = st.selectbox("Material", raw_materials)
                        mat_qty = st.number_input("Quantity (Kg)", min_value=0.0, step=0.1)
                        if st.form_submit_button("Add to Mill"):
                            ts = str(int(datetime.now().timestamp()))
                            entry = {
                                "Date": datetime.now(), "Type": "Mill_Consumption", "ID": f"ADD-{ts}",
                                "Ball_Mill_ID": active_mill, "Item_Name": mat_item,
                                "Quantity": -mat_qty, "Unit": "Kg"
                            }
                            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                            st.success("Added!")

            elif action_type == "Finish & Produce Bags":
                if not grades:
                     st.warning("No Grades defined.")
                     if st.button("➕ Add Grades"): navigate_to("8. Master Data")
                else:
                    with st.form("finish_mill"):
                        out_grade = st.selectbox("Produced Grade", grades)
                        bags = st.number_input("No. of Bags Produced", min_value=1)
                        if st.form_submit_button("Finish Process"):
                            ts = str(int(datetime.now().timestamp()))
                            entry = {
                                "Date": datetime.now(), "Type": "Mill_Production", "ID": f"FIN-{ts}",
                                "Ball_Mill_ID": active_mill, "Item_Name": out_grade,
                                "Quantity": bags, "Unit": "Bags", "Status": "Completed"
                            }
                            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                            st.success(f"Production Recorded! {bags} Bags of {out_grade}")

    # ==========================================
    # 4. SALES
    # ==========================================
    elif choice == "4. Sales":
        st.header("🚚 Sales Entry")
        
        col_check1, col_check2 = st.columns(2)
        if not customers:
            col_check1.warning("⚠️ No Customers found.")
            if col_check1.button("➕ Add Customer"): navigate_to("8. Master Data")
        
        if not grades:
            col_check2.warning("⚠️ No Grades found.")
            if col_check2.button("➕ Add Grade"): navigate_to("8. Master Data")
            
        if customers and grades:
            with st.form("sales_entry"):
                s_date = st.date_input("Date", datetime.now())
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

    # ==========================================
    # 5. PURCHASE
    # ==========================================
    elif choice == "5. Purchase":
        st.header("🛒 Purchase Entry")
        
        col_check1, col_check2 = st.columns(2)
        if not suppliers:
            col_check1.warning("⚠️ No Suppliers found.")
            if col_check1.button("➕ Add Supplier"): navigate_to("8. Master Data")
        
        if not raw_materials:
            col_check2.warning("⚠️ No Items found.")
            if col_check2.button("➕ Add Item"): navigate_to("8. Master Data")

        if suppliers and raw_materials:
            with st.form("purchase_form"):
                col1, col2 = st.columns(2)
                date = col1.date_input("Date", datetime.now())
                supplier = col2.selectbox("Supplier", suppliers)
                
                col3, col4, col5 = st.columns(3)
                item = col3.selectbox("Item", raw_materials)
                qty = col4.number_input("Quantity", min_value=0.0, step=0.1)
                unit = col5.selectbox("Unit", ["Kg", "Litres", "Pieces"])
                
                notes = st.text_input("Invoice No / Notes")
                
                if st.form_submit_button("Save Purchase"):
                    new_id = get_next_id(df, "PUR")
                    entry = {
                        "Date": date, "Type": "Purchase", "ID": new_id, 
                        "Party_Name": supplier, "Item_Name": item, 
                        "Quantity": qty, "Unit": unit, "Status": "In Stock", "Notes": notes
                    }
                    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
                    save_data(df, TRANS_FILE)
                    st.success(f"Saved! ID: {new_id}")

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
        st.header("💾 Raw Data Log")
        st.info("You can edit cells here to fix mistakes. Click 'Save' after editing.")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        
        if st.button("Save Changes to Database"):
            save_data(edited_df, TRANS_FILE)
            st.success("Changes saved permanently!")

    # ==========================================
    # 8. MASTER DATA (With Search)
    # ==========================================
    elif choice == "8. Master Data":
        st.header("🛠️ Master Data Management")
        st.markdown("Add new Items, Suppliers, or Customers here.")
        
        c1, c2 = st.columns([1, 2])
        
        # COLUMN 1: ADD NEW
        with c1:
            st.subheader("Add New")
            with st.form("add_master"):
                m_type = st.selectbox("Type", ["Material", "Grade", "Supplier", "Customer"])
                m_name = st.text_input("Name (e.g., Urea, ABC Chemicals)")
                
                # Opening Stock
                opening_stock = 0.0
                if m_type in ["Material", "Grade"]:
                    st.markdown("---")
                    st.caption("Does this item have Opening Stock?")
                    opening_stock = st.number_input("Opening Quantity", min_value=0.0, step=0.1)
                
                submit = st.form_submit_button("Add to Master")
                
                if submit and m_name:
                    if m_name in masters[masters['Type'] == m_type]['Name'].values:
                        st.error("Already exists!")
                    else:
                        new_row = {"Type": m_type, "Name": m_name}
                        masters = pd.concat([masters, pd.DataFrame([new_row])], ignore_index=True)
                        save_data(masters, MASTERS_FILE)
                        
                        if opening_stock > 0:
                            unit = "Bags" if m_type == "Grade" else "Kg"
                            op_entry = {
                                "Date": datetime.now(), "Type": "Opening Stock", "ID": get_next_id(df, "OPN"),
                                "Item_Name": m_name, "Quantity": opening_stock, "Unit": unit, 
                                "Status": "Stock In", "Notes": "Initial Balance"
                            }
                            df = pd.concat([df, pd.DataFrame([op_entry])], ignore_index=True)
                            save_data(df, TRANS_FILE)
                            st.success(f"Added {m_name} with {opening_stock} {unit} stock!")
                        else:
                            st.success(f"Added {m_name}")
                        st.rerun()

        # COLUMN 2: SEARCHABLE LIST
        with c2:
            st.subheader("Existing List")
            
            # --- NEW SEARCH FEATURE ---
            # Search logic: "starts with" based on user request
            search_query = st.text_input("🔍 Search from first letter")
            
            if search_query:
                # Filter: Case-insensitive "Starts With"
                mask = masters['Name'].str.lower().str.startswith(search_query.lower())
                display_df = masters[mask]
            else:
                display_df = masters
                
            st.dataframe(display_df, use_container_width=True)

if __name__ == "__main__":
    main()
