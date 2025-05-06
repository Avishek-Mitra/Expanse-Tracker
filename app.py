from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
import json
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
from matplotlib.figure import Figure
import numpy as np

app = Flask(__name__)

# Ensure the instance folder exists
if not os.path.exists('instance'):
    os.makedirs('instance')

# Initialize database
def init_db():
    conn = sqlite3.connect('instance/expenses.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# Helper functions
def get_expenses():
    conn = sqlite3.connect('instance/expenses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM expenses ORDER BY date DESC')
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses

def add_expense(description, amount, category, date):
    conn = sqlite3.connect('instance/expenses.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO expenses (description, amount, category, date) VALUES (?, ?, ?, ?)',
        (description, amount, category, date)
    )
    conn.commit()
    conn.close()

def delete_expense(expense_id):
    conn = sqlite3.connect('instance/expenses.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    conn.commit()
    conn.close()

def get_expense_summary():
    expenses = get_expenses()
    
    # Total expenses
    total = sum(expense['amount'] for expense in expenses)
    
    # Current month expenses
    current_month = datetime.now().strftime('%Y-%m')
    current_month_expenses = [
        expense for expense in expenses 
        if expense['date'].startswith(current_month)
    ]
    current_month_total = sum(expense['amount'] for expense in current_month_expenses)
    
    # Expenses by category
    categories = {}
    for expense in expenses:
        category = expense['category']
        if category not in categories:
            categories[category] = 0
        categories[category] += expense['amount']
    
    return {
        'total': total,
        'current_month_total': current_month_total,
        'categories': categories
    }

def generate_category_chart():
    summary = get_expense_summary()
    categories = summary['categories']
    
    if not categories:
        return None
    
    # Create figure
    fig = Figure(figsize=(6, 6))
    ax = fig.add_subplot(111)
    
    # Create pie chart
    labels = list(categories.keys())
    values = list(categories.values())
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    
    # Save to base64 string
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return chart_data

def generate_daily_chart():
    conn = sqlite3.connect('instance/expenses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get expenses for the last 7 days
    cursor.execute('''
    SELECT date, SUM(amount) as total 
    FROM expenses 
    WHERE date >= date('now', '-7 days') 
    GROUP BY date 
    ORDER BY date
    ''')
    
    daily_data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    if not daily_data:
        return None
    
    # Create figure
    fig = Figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    
    dates = [row['date'] for row in daily_data]
    amounts = [row['total'] for row in daily_data]
    
    # Create bar chart
    bars = ax.bar(dates, amounts, color='skyblue')
    
    # Add labels
    ax.set_xlabel('Date')
    ax.set_ylabel('Amount ($)')
    ax.set_title('Daily Expenses (Last 7 Days)')
    
    # Rotate date labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'${height:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    fig.tight_layout()
    
    # Save to base64 string
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    return chart_data

# Routes
@app.route('/')
def index():
    expenses = get_expenses()
    summary = get_expense_summary()
    category_chart = generate_category_chart()
    daily_chart = generate_daily_chart()
    
    # Get unique categories for filter dropdown
    categories = set(expense['category'] for expense in expenses)
    
    return render_template(
        'index.html', 
        expenses=expenses, 
        summary=summary, 
        categories=categories,
        category_chart=category_chart,
        daily_chart=daily_chart
    )

@app.route('/add_expense', methods=['POST'])
def add_expense_route():
    description = request.form.get('description')
    amount = float(request.form.get('amount'))
    category = request.form.get('category')
    date = request.form.get('date')
    
    add_expense(description, amount, category, date)
    return redirect(url_for('index'))

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense_route(expense_id):
    delete_expense(expense_id)
    return redirect(url_for('index'))

@app.route('/filter_expenses', methods=['GET'])
def filter_expenses():
    search_term = request.args.get('search', '').lower()
    category_filter = request.args.get('category', '')
    
    conn = sqlite3.connect('instance/expenses.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = 'SELECT * FROM expenses WHERE 1=1'
    params = []
    
    if search_term:
        query += ' AND LOWER(description) LIKE ?'
        params.append(f'%{search_term}%')
    
    if category_filter and category_filter != 'all':
        query += ' AND category = ?'
        params.append(category_filter)
    
    query += ' ORDER BY date DESC'
    
    cursor.execute(query, params)
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(expenses=expenses)

if __name__ == '__main__':
    app.run(debug=True)