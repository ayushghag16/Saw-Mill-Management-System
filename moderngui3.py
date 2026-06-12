# moderngui3.py
import sys
import os
import mysql.connector
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QLineEdit, QFormLayout, QHeaderView, QDialog, QDialogButtonBox, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

# ReportLab for PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# ---------- DB Connection ----------
def get_connection():
    return mysql.connector.connect(
        host="localhost", user="root", password="ayush@123", database="sawmill_db"
    )


def get_dropdown_data(table, id_col, name_col):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {id_col}, {name_col} FROM {table}")
    data = cursor.fetchall()
    conn.close()
    return data


# ---------- Sidebar Button ----------
class SidebarButton(QPushButton):
    def __init__(self, text, icon="", parent=None):
        super().__init__(f"{icon}  {text}", parent)
        self.setFixedHeight(45)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2d3436;
                color: white;
                border: none;
                font-size: 15px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background-color: #636e72;
            }
            QPushButton:checked {
                background-color: #0984e3;
            }
        """)
        self.setCheckable(True)


# ---------- Form Dialog (single form for Add/Edit) ----------
class FormDialog(QDialog):
    def __init__(self, col_labels, col_names, foreign_keys=None, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Record")
        self.foreign_keys = foreign_keys or {}
        self.col_names = col_names
        layout = QFormLayout()
        self.widgets = {}

        # create widgets for columns except id (index 0)
        for i, col in enumerate(col_names[1:]):
            label = col_labels[i + 1] if i + 1 < len(col_labels) else col
            if col in self.foreign_keys:
                table, id_col, name_col = self.foreign_keys[col]
                options = get_dropdown_data(table, id_col, name_col)
                combo = QComboBox()
                for oid, name in options:
                    combo.addItem(str(name), oid)
                # try prefill if data provided (data list indexed same as columns)
                if data:
                    cur_val = str(data[i + 1])
                    for idx in range(combo.count()):
                        if combo.itemText(idx) == cur_val:
                            combo.setCurrentIndex(idx)
                            break
                self.widgets[col] = combo
                layout.addRow(label + " :", combo)
            else:
                edit = QLineEdit()
                if data:
                    edit.setText(str(data[i + 1]))
                self.widgets[col] = edit
                layout.addRow(label + " :", edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.setMinimumWidth(420)

    def get_values(self):
        vals = []
        # maintain same order as col_names[1:]
        for col in self.col_names[1:]:
            widget = self.widgets.get(col)
            if widget is None:
                vals.append(None)
            elif isinstance(widget, QComboBox):
                vals.append(widget.currentData())
            else:
                vals.append(widget.text())
        return vals


# ---------- Generic CRUD Page ----------
class CRUDPage(QWidget):
    def __init__(self, table_name, columns, col_labels, foreign_keys=None):
        super().__init__()
        self.table_name = table_name
        self.columns = columns
        self.col_labels = col_labels
        self.foreign_keys = foreign_keys or {}

        layout = QVBoxLayout()
        title = QLabel(f"🔧 {table_name.replace('_', ' ').title()} Management")
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(col_labels)

        # Styling for readability
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #f5f6fa; alternate-background-color: #ffffff; }
            QHeaderView::section { background-color: #0984e3; color: white; font-weight: bold; padding: 4px; }
        """)
        # Auto-fit and stretch columns
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add")
        self.edit_btn = QPushButton("✏️ Edit")
        self.delete_btn = QPushButton("🗑️ Delete")
        self.refresh_btn = QPushButton("🔄 Refresh")
        for b in (self.add_btn, self.edit_btn, self.delete_btn, self.refresh_btn):
            b.setStyleSheet("background:#0984e3; color:white; padding:6px; border-radius:5px;")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Connect actions
        self.add_btn.clicked.connect(self.add_record)
        self.edit_btn.clicked.connect(self.edit_record)
        self.delete_btn.clicked.connect(self.delete_record)
        self.refresh_btn.clicked.connect(self.load_data)

        self.load_data()

    def load_data(self):
        """Load all rows from the DB and update the table widget."""
        try:
            self.table.setRowCount(0)
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self.table_name}")
            rows = cursor.fetchall()
            for row_idx, row_data in enumerate(rows):
                self.table.insertRow(row_idx)
                for col_idx, col_data in enumerate(row_data):
                    item = QTableWidgetItem(str(col_data) if col_data is not None else "")
                    item.setToolTip(str(col_data) if col_data is not None else "")
                    item.setFlags(item.flags())  # keep editable if you'd like (not disabling)
                    # center align for numeric-ish columns
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.table.setItem(row_idx, col_idx, item)

            # Improve presentation
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            self.table.horizontalHeader().setStretchLastSection(True)
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Failed to load {self.table_name}: {e}")

    def add_record(self):
        """Open a single form dialog to collect all fields at once and insert."""
        dialog = FormDialog(self.col_labels, self.columns, self.foreign_keys, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            # remove None values and keep placeholders in sync with columns
            placeholders = ",".join(["%s"] * len(values))
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    f"INSERT INTO {self.table_name} ({','.join(self.columns[1:])}) VALUES ({placeholders})",
                    values
                )
                conn.commit()
                conn.close()
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Insert Error", str(e))

    def edit_record(self):
        """Open form pre-filled with selected row, then update on OK."""
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Error", "Please select a row to edit")
            return

        record_id = self.table.item(row, 0).text()
        # gather current row data
        data = []
        for c in range(self.table.columnCount()):
            item = self.table.item(row, c)
            data.append(item.text() if item else "")

        dialog = FormDialog(self.col_labels, self.columns, self.foreign_keys, data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            try:
                conn = get_connection()
                cursor = conn.cursor()
                set_clause = ",".join([f"{col}=%s" for col in self.columns[1:]])
                cursor.execute(
                    f"UPDATE {self.table_name} SET {set_clause} WHERE {self.columns[0]}=%s",
                    values + [record_id]
                )
                conn.commit()
                conn.close()
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Update Error", str(e))

    def delete_record(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Error", "Please select a row to delete")
            return
        record_id = self.table.item(row, 0).text()
        confirm = QMessageBox.question(self, "Confirm", f"Delete record {record_id}?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {self.table_name} WHERE {self.columns[0]}=%s", (record_id,))
                conn.commit()
                conn.close()
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", str(e))


# ---------- Invoice Page ----------
class InvoicePage(CRUDPage):
    def __init__(self):
        super().__init__(
            "billing_invoices",
            ["invoice_id", "order_id", "invoice_date", "total_amount", "payment_status"],
            ["ID", "Order", "Date", "Total", "Payment"],
            {"order_id": ("orders", "order_id", "order_id")}
        )
        self.generate_btn = QPushButton("📄 Generate Invoice")
        self.generate_btn.setStyleSheet("background:#00b894; color:white; padding:6px; border-radius:5px;")
        self.layout().addWidget(self.generate_btn)
        self.generate_btn.clicked.connect(self.generate_invoice)

    def generate_invoice(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Error", "Select an invoice")
            return

        invoice_id = self.table.item(row, 0).text()
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT i.invoice_id,i.invoice_date,i.total_amount,i.payment_status,
                   o.order_id,o.quantity,o.total_amount AS order_total,
                   c.name AS customer_name,c.contact_number,c.address,
                   p.product_name,p.price_per_unit
            FROM billing_invoices i
            JOIN orders o ON i.order_id=o.order_id
            JOIN customers c ON o.customer_id=c.customer_id
            JOIN products p ON o.product_id=p.product_id
            WHERE i.invoice_id=%s
        """, (invoice_id,))
        data = cursor.fetchone()
        conn.close()
        if not data:
            QMessageBox.warning(self, "Error", "No data found")
            return

        os.makedirs("invoices", exist_ok=True)
        file_path = f"invoices/invoice_{invoice_id}.pdf"

        c = canvas.Canvas(file_path, pagesize=A4)
        w, h = A4

        # Company Logo + Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(40, h - 60, "Sai Krupa Sawmill")
        c.setFont("Helvetica", 10)
        c.drawString(40, h - 75, "Opp. to Main Post Office, Near CHH. Shivaji Maharaj Statue,Malegaon ,Nashik, Maharashtra - 423203")
        c.drawString(40, h - 90, "Phone: +91-9422246040")

        # Invoice Title bar
        c.setFillColorRGB(0.1, 0.5, 0.8)
        c.rect(0, h - 130, w, 25, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 122, "INVOICE")

        # Invoice Info (ID + Date)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, h - 160, f"Invoice #: {data['invoice_id']}")
        c.drawString(300, h - 160, f"Date: {data['invoice_date']}")

        # Customer Box
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, h - 190, "Bill To:")
        c.setFont("Helvetica", 11)
        c.drawString(110, h - 195, data['customer_name'])
        c.drawString(110, h - 210, data['contact_number'])
        c.drawString(110, h - 225, data['address'][:35])  # wrap if long

        # Table Header
        y = h - 270
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(40, y, w - 80, 20, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.drawString(50, y + 5, "Product")
        c.drawString(250, y + 5, "Quantity")
        c.drawString(350, y + 5, "Rate")
        c.drawString(450, y + 5, "Total")

        # Table Data
        y -= 25
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0, 0, 0)
        product_total = data['quantity'] * data['price_per_unit']
        c.rect(40, y, w - 80, 20, fill=0)
        c.drawString(50, y + 5, data['product_name'])
        c.drawString(250, y + 5, str(data['quantity']))
        c.drawString(350, y + 5, f"{data['price_per_unit']}")
        c.drawString(450, y + 5, f"{product_total}")

        # Grand Total Box
        y -= 50
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(350, y, 190, 40, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(360, y + 25, "Grand Total:")
        c.drawString(460, y + 25, f"{data['total_amount']}")
        c.setFont("Helvetica", 11)
        c.drawString(360, y + 10, "Payment Status:")
        c.drawString(460, y + 10, data['payment_status'])

        # Footer
        c.setFont("Helvetica-Oblique", 10)
        c.drawCentredString(w / 2, 80, "Thank you for your business!")
        c.drawRightString(w - 50, 80, "Authorized Signatory")

        c.showPage()
        c.save()

        QMessageBox.information(self, "Done", f"Invoice saved: {file_path}")
        try:
            os.startfile(file_path)  # Windows
        except Exception:
            pass


# ---------- Dashboard ----------
class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Summary cards
        stats_layout = QHBoxLayout()
        for name, table, icon in [
            ("Employees", "employees", "👨‍💼"),
            ("Products", "products", "📦"),
            ("Customers", "customers", "👥"),
            ("Orders", "orders", "📄"),
            ("Invoices", "billing_invoices", "💰")
        ]:
            count = self.get_count(table)
            card = QLabel(f"{icon}\n{name}\n{count}")
            card.setAlignment(Qt.AlignCenter)
            card.setStyleSheet("background:#dfe6e9; padding:15px; font-size:16px; border-radius:10px;")
            stats_layout.addWidget(card)
        layout.addLayout(stats_layout)

        # Sales chart
        fig, ax = plt.subplots(figsize=(6, 2.5))
        months, sales = self.get_sales_data()
        if months:
            ax.bar(months, sales, color="#0984e3")
            ax.set_title("Sales")
        else:
            ax.text(0.5, 0.5, "No Sales Data", ha='center')
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        # Pending invoices
        label = QLabel("🕒 Pending Invoices")
        label.setStyleSheet("font-size:18px; margin-top:15px;")
        layout.addWidget(label)
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(4)
        self.pending_table.setHorizontalHeaderLabels(["Invoice ID", "Order ID", "Amount", "Status"])
        self.pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.pending_table)
        self.load_pending_invoices()

        self.setLayout(layout)

    def get_count(self, table):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]; conn.close()
            return count
        except Exception:
            return 0

    def get_sales_data(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("""
                SELECT DATE_FORMAT(order_date,'%b %Y') as month, SUM(total_amount)
                FROM orders GROUP BY month ORDER BY MAX(order_date) DESC LIMIT 6
            """)
            data = cursor.fetchall(); conn.close()
            if not data:
                return [], []
            months = [d[0] for d in data][::-1]; sales = [float(d[1]) for d in data][::-1]
            return months, sales
        except Exception:
            return [], []

    def load_pending_invoices(self):
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT invoice_id, order_id, total_amount, payment_status FROM billing_invoices WHERE payment_status IN ('unpaid','partially_paid')")
            data = cursor.fetchall(); conn.close()
            self.pending_table.setRowCount(0)
            for r, row in enumerate(data):
                self.pending_table.insertRow(r)
                for c, val in enumerate(row):
                    self.pending_table.setItem(r, c, QTableWidgetItem(str(val)))
            self.pending_table.resizeColumnsToContents()
        except Exception:
            pass


# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sai Krupa Sawmill")
        self.setGeometry(200, 100, 1200, 750)

        main_widget = QWidget(); main_layout = QVBoxLayout(main_widget)

        # Topbar
        topbar = QFrame(); topbar.setFixedHeight(50); topbar.setStyleSheet("background:#1e272e; color:white;")
        title = QLabel("🌲 Sai Krupa Sawmill"); title.setStyleSheet("font-size:18px; font-weight:bold; padding-left:15px; color:white;")
        logout = QPushButton("Logout"); logout.setStyleSheet("background:#d63031; color:white; padding:5px; border-radius:5px;")
        logout.clicked.connect(self.logout)
        top_layout = QHBoxLayout(topbar); top_layout.addWidget(title); top_layout.addStretch(); top_layout.addWidget(logout)
        main_layout.addWidget(topbar)

        # Content
        content_layout = QHBoxLayout()
        sidebar = QFrame(); sidebar.setFixedWidth(220); sidebar.setStyleSheet("background:#2d3436;")
        sidebar_layout = QVBoxLayout(sidebar)

        self.buttons = []; self.stack = QStackedWidget()
        self.sections = {
            "Dashboard": Dashboard(),
            "Employees": CRUDPage("employees", ["employee_id", "name", "role", "contact_number"], ["ID", "Name", "Role", "Contact"]),
            "Employee Salary": CRUDPage("employee_salary", ["salary_id", "employee_id", "month", "basic_salary", "allowances", "deductions", "net_salary"],
                                       ["ID", "Employee", "Month", "Basic", "Allowances", "Deductions", "Net"], {"employee_id": ("employees", "employee_id", "name")}),
            "Suppliers": CRUDPage("suppliers", ["supplier_id", "name", "contact_number", "email", "address"], ["ID", "Name", "Contact", "Email", "Address"]),
            "Raw Materials": CRUDPage("raw_materials", ["material_id", "material_name", "unit", "price_per_unit", "supplier_id"], ["ID", "Name", "Unit", "Price", "Supplier"], {"supplier_id": ("suppliers", "supplier_id", "name")}),
            "Products": CRUDPage("products", ["product_id", "product_name", "description", "unit", "price_per_unit"], ["ID", "Name", "Description", "Unit", "Price"]),
            "Customers": CRUDPage("customers", ["customer_id", "name", "contact_number", "email", "address"], ["ID", "Name", "Contact", "Email", "Address"]),
            "Stock Transactions": CRUDPage("stock_transactions", ["transaction_id", "material_id", "supplier_id", "transaction_type", "quantity", "total_cost", "transaction_date", "remarks"],
                                          ["ID", "Material", "Supplier", "Type", "Quantity", "Cost", "Date", "Remarks"], {"material_id": ("raw_materials", "material_id", "material_name"), "supplier_id": ("suppliers", "supplier_id", "name")}),
            "Orders": CRUDPage("orders", ["order_id", "customer_id", "product_id", "quantity", "total_amount", "order_date", "delivery_date", "delivery_agent", "vehicle_number", "delivery_status", "status"],
                              ["ID", "Customer", "Product", "Qty", "Amount", "Order Date", "Delivery Date", "Agent", "Vehicle", "Delivery Status", "Status"],
                              {"customer_id": ("customers", "customer_id", "name"), "product_id": ("products", "product_id", "product_name")}),
            "Invoices": InvoicePage(),
        }

        icons = {"Dashboard": "📊", "Employees": "👨‍💼", "Employee Salary": "💵", "Suppliers": "🏭", "Raw Materials": "🪵", "Products": "📦", "Customers": "👥", "Stock Transactions": "📑", "Orders": "📄", "Invoices": "📄", "Admins": "🔑"}
        for section, page in self.sections.items():
            btn = SidebarButton(section, icons.get(section, ""))
            btn.section_name = section
            btn.clicked.connect(self.handle_sidebar_click)
            sidebar_layout.addWidget(btn)
            self.buttons.append(btn)
            self.stack.addWidget(page)

        sidebar_layout.addStretch()
        content_layout.addWidget(sidebar); content_layout.addWidget(self.stack)
        main_layout.addLayout(content_layout)
        self.setCentralWidget(main_widget)

        # Default page
        if self.buttons:
            self.buttons[0].setChecked(True)
            self.stack.setCurrentWidget(self.sections["Dashboard"])

    def handle_sidebar_click(self):
        clicked = self.sender()
        for b in self.buttons:
            b.setChecked(b == clicked)
        section_name = clicked.section_name
        if section_name in self.sections:
            self.stack.setCurrentWidget(self.sections[section_name])

    def logout(self):
        self.close()
        self.login = LoginWindow()
        self.login.show()


# ---------- Login Window ----------
class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Sai Krupa Sawmill")
        self.setGeometry(400, 200, 400, 300)
        layout = QVBoxLayout(self)

        logo = QLabel(); pixmap = QPixmap("logo.png")
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)

        title = QLabel("🌲 Sai Krupa Sawmill")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.user_input = QLineEdit(); self.user_input.setPlaceholderText("Username")
        self.pass_input = QLineEdit(); self.pass_input.setPlaceholderText("Password"); self.pass_input.setEchoMode(QLineEdit.Password)
        form.addRow("Username:", self.user_input); form.addRow("Password:", self.pass_input)
        layout.addLayout(form)

        self.login_btn = QPushButton("Login")
        self.login_btn.setStyleSheet("background:#0984e3; color:white; padding:8px; border-radius:5px;")
        layout.addWidget(self.login_btn)
        self.login_btn.clicked.connect(self.check_login)

    def check_login(self):
        user = self.user_input.text(); pwd = self.pass_input.text()
        try:
            conn = get_connection(); cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin_users WHERE username=%s AND password_hash=%s", (user, pwd))
            result = cursor.fetchone(); conn.close()
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Login failed: {e}")
            return

        if result:
            self.main = MainWindow(); self.main.show(); self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")


# ---------- Run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow(); login.show()
    sys.exit(app.exec_())
