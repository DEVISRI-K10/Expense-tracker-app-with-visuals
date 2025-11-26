import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime, date
import os

# Page config
st.set_page_config(page_title="Expense Tracker", layout="wide")

# Session state for data and budget
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=['Date', 'Category', 'Amount', 'Description'])
if 'budget' not in st.session_state:
    st.session_state.budget = 0.0

# Categories
CATEGORIES = ['Food', 'Transport', 'Entertainment', 'Utilities', 'Health', 'Shopping', 'Other']

# Sidebar: Input Form + Budget + Upload
st.sidebar.header("Add Expense")
col1, col2 = st.sidebar.columns(2)
with col1:
    expense_date = st.date_input("Date", value=date.today())
with col2:
    category = st.selectbox("Category", CATEGORIES)
amount = st.sidebar.number_input("Amount", min_value=0.0, format="%.2f")
description = st.sidebar.text_input("Description")
if st.sidebar.button("Add Expense"):
    if amount > 0:
        new_row = pd.DataFrame({
            'Date': [pd.to_datetime(expense_date)],
            'Category': [category],
            'Amount': [amount],
            'Description': [description or 'N/A']
        })
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
        st.sidebar.success("Added!")
        st.rerun()
    else:
        st.sidebar.error("Amount must be > 0")

# Budget
st.sidebar.header("Budget")
budget_input = st.sidebar.number_input("Monthly Budget", value=st.session_state.budget, format="%.2f")
if st.sidebar.button("Set Budget"):
    st.session_state.budget = budget_input
    st.rerun()

# CSV Upload
uploaded_file = st.sidebar.file_uploader("Upload CSV", type='csv')
if uploaded_file is not None:
    df_upload = pd.read_csv(uploaded_file)
    if all(col in df_upload.columns for col in ['Date', 'Category', 'Amount']):
        df_upload['Date'] = pd.to_datetime(df_upload['Date'], errors='coerce')
        df_upload['Amount'] = pd.to_numeric(df_upload['Amount'], errors='coerce')
        df_upload = df_upload.dropna()
        df_upload['Category'] = df_upload['Category'].apply(lambda x: x if x in CATEGORIES else 'Other')
        df_upload['Description'] = df_upload.get('Description', 'N/A').fillna('N/A')
        st.session_state.df = pd.concat([st.session_state.df, df_upload], ignore_index=True)
        st.sidebar.success(f"Uploaded {len(df_upload)} rows!")
        st.rerun()

# Clean data function
@st.cache_data
def clean_data(df):
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
    df = df.dropna()
    df['Category'] = df['Category'].apply(lambda x: x if x in CATEGORIES else 'Other')
    df['Month'] = df['Date'].dt.to_period('M')
    return df

# Main dashboard
st.title("📊 Expense Tracker Dashboard")
df_clean = clean_data(st.session_state.df)

if df_clean.empty:
    st.info("👆 Add expenses via sidebar or upload CSV to get started!")
else:
    # Budget Alert
    if st.session_state.budget > 0:
        current_month = df_clean['Month'].max()
        monthly_total = df_clean[df_clean['Month'] == current_month]['Amount'].sum()
        if monthly_total > st.session_state.budget:
            st.error(f"🚨 Budget Alert! Spent \( {monthly_total:.2f} this month (over \){st.session_state.budget:.2f} by ${monthly_total - st.session_state.budget:.2f})")

    # Metrics
    col1, col2, col3 = st.columns(3)
    total_spent = df_clean['Amount'].sum()
    col1.metric("Total Spent", f"${total_spent:.2f}")
    avg_monthly = df_clean.groupby('Month')['Amount'].sum().mean()
    col2.metric("Avg Monthly", f"${avg_monthly:.2f}")
    num_entries = len(df_clean)
    col3.metric("Entries", num_entries)

    # Table
    st.subheader("📋 Expenses Table")
    st.dataframe(df_clean[['Date', 'Category', 'Amount', 'Description']].style.format({'Amount': '${:.2f}'}), use_container_width=True)

    # Charts
    st.subheader("📈 Visual Insights")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### By Category (Pie)")
        fig_pie, ax_pie = plt.subplots()
        cat_sum = df_clean.groupby('Category')['Amount'].sum()
        ax_pie.pie(cat_sum.values, labels=cat_sum.index, autopct='%1.1f%%', startangle=90)
        ax_pie.set_title('Expenses by Category')
        st.pyplot(fig_pie)

    with col2:
        st.markdown("### Monthly Trend (Bar)")
        fig_bar, ax_bar = plt.subplots()
        monthly_sum = df_clean.groupby('Month')['Amount'].sum()
        monthly_sum.plot(kind='bar', ax=ax_bar, color='skyblue')
        ax_bar.set_title('Monthly Expenses')
        ax_bar.set_xlabel('Month')
        ax_bar.set_ylabel('Amount ($)')
        plt.xticks(rotation=45)
        st.pyplot(fig_bar)

    # Export
    st.subheader("📥 Export Report")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_clean.to_excel(writer, sheet_name='Expenses', index=False)
        summary_cat = df_clean.groupby('Category')['Amount'].sum().to_frame()
        summary_cat.to_excel(writer, sheet_name='Category Summary')
        summary_month = df_clean.groupby('Month')['Amount'].sum().to_frame()
        summary_month.to_excel(writer, sheet_name='Monthly Summary')
    st.download_button(
        label="Download Excel Report",
        data=output.getvalue(),
        file_name=f'expense_report_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # Data cleaning note
    st.caption("Data is auto-cleaned: Dates parsed, amounts numeric, uncategorized → 'Other'.")