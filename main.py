import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QLabel, QComboBox, QLineEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QMessageBox)

class BannerStock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Estoque Banner")
        self.setGeometry(100, 100, 800, 600)
        
        self.db_connection = sqlite3.connect('stock.db')
        self.create_tables()

        self.products = self.get_products()
        self.initUI()

    def create_tables(self):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS input_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT (DATETIME('now', '-3 hours'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS output_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT (DATETIME('now', '-3 hours'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balanced_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product TEXT NOT NULL UNIQUE,
                current_stock INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT (DATETIME('now', '-3 hours'))
            )
        ''')
        self.db_connection.commit()

    def get_products(self):
        return ['-', '11 10.5-19', '11 10.5-21', '11 10.5K-25', '11 10.5E-16', '11 10.5E-18', '5S 8-16.5',
                '5S 8A -19', '5S 8A-16.5', '5S 8E-18', '5S 8K-17.5', '5S 8M -16', '5S 8N-13', '6174 N (LTS)',
                '9 10-16', '9 10-18-5', '9 10-19', '9 10-21', '9 95SP-14-4', '9 9KS-17.5', '9 9LS-13.5', '9 9S - 12']

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        self.product_dropdown = QComboBox()
        self.product_dropdown.addItems(self.products)
        layout.addWidget(QLabel("Selecione a referência: "))
        layout.addWidget(self.product_dropdown)

        self.stock_input = QLineEdit()
        layout.addWidget(QLabel('Quantidade: '))
        layout.addWidget(self.stock_input)

        self.add_stock_button = QPushButton('Adicionar ao estoque')
        self.add_stock_button.clicked.connect(self.add_stock)
        layout.addWidget(self.add_stock_button)

        self.reduce_stock_button = QPushButton('Retirar do estoque')
        self.reduce_stock_button.clicked.connect(self.reduce_stock)
        layout.addWidget(self.reduce_stock_button)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(2)
        self.stock_table.setHorizontalHeaderLabels(['Produto', 'Saldo'])
        layout.addWidget(QLabel("Estoque Atual (Diferença entre entradas e saídas)"))
        layout.addWidget(self.stock_table)
        
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(3)
        self.transactions_table.setHorizontalHeaderLabels(['Produto','Qtd movimentada','Hora da movimentação'])
        layout.addWidget(QLabel('Últimas movimentações'))
        layout.addWidget(self.transactions_table)

        self.load_db()
        self.load_transactions()

        central_widget.setLayout(layout)

    def load_db(self):
        cursor = self.db_connection.cursor()
        
        cursor.execute('SELECT product, SUM(quantity) FROM input_stock GROUP BY product ')
        input_stock_data = cursor.fetchall()
        
        cursor.execute('SELECT product, SUM(quantity) FROM output_stock GROUP BY product')
        output_stock_data = cursor.fetchall()
        
        input_dict = {row[0]: row[1] for row in input_stock_data}
        output_dict = {row[0]: row[1] for row in output_stock_data}
        
        all_products = set(input_dict.keys()).union(output_dict.keys())
        
        rows = []
        for product in all_products:
            total_input = input_dict.get(product, 0)
            total_output = output_dict.get(product, 0)
            balance = total_input - total_output
            rows.append((product, total_input, total_output, balance))
        
        self.stock_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self.stock_table.setItem(row_index, 0, QTableWidgetItem(row[0]))
            self.stock_table.setItem(row_index, 1, QTableWidgetItem(f'{row[3]} bobinas'))
            
    def load_transactions(self):
        cursor = self.db_connection.cursor()

        cursor.execute('''
            SELECT product, quantity, updated_at, 'Entrada' as tipo
            FROM input_stock
            UNION ALL
            SELECT product, quantity, updated_at, 'Saída' as tipo
            FROM output_stock
            ORDER BY updated_at DESC
        ''')
        transactions = cursor.fetchall()

        self.transactions_table.setRowCount(len(transactions))
        self.transactions_table.setColumnCount(4)
        self.transactions_table.setHorizontalHeaderLabels(['Produto', 'Qtd movimentada', 'Hora da movimentação', 'Tipo'])

        for row_index, row in enumerate(transactions):
            self.transactions_table.setItem(row_index, 0, QTableWidgetItem(str(row[0])))
            self.transactions_table.setItem(row_index, 1, QTableWidgetItem(f'{row[1]} bobinas'))
            self.transactions_table.setItem(row_index, 2, QTableWidgetItem(str(row[2])))
            self.transactions_table.setItem(row_index, 3, QTableWidgetItem(str(row[3])))
        
        self.transactions_table.resizeColumnsToContents()

    def add_stock(self):
        self.modify_stock(operation='add_to_stock')

    def reduce_stock(self):
        self.modify_stock(operation='remove_from_stock')
        
    def rebalance_stock(self, product):
        cursor = self.db_connection.cursor()
        
        cursor.execute('SELECT SUM(quantity) FROM input_stock WHERE product = ?', (product,))
        input_stock_data = cursor.fetchone()
        
        cursor.execute('SELECT SUM(quantity) FROM output_stock WHERE product = ?', (product,))
        output_stock_data = cursor.fetchone()
        
        total_input = input_stock_data[0] if input_stock_data[0] is not None else 0
        total_output = output_stock_data[0] if output_stock_data[0] is not None else 0
        balance = total_input - total_output
        
        cursor.execute('''
            INSERT INTO balanced_stock (product, current_stock) VALUES (?, ?)
            ON CONFLICT(product) DO UPDATE SET current_stock = ?
        ''', (product, balance, balance))
         
        self.db_connection.commit()

    def modify_stock(self, operation):
        product = self.product_dropdown.currentText()
        quantity = self.stock_input.text()

        if not quantity.isdigit():
            QMessageBox.warning(self, "Erro", "Insira apenas números")
            return

        quantity = int(quantity)
        
        cursor = self.db_connection.cursor()
        
        if operation == 'add_to_stock':
            cursor.execute('INSERT INTO input_stock (product, quantity) VALUES (?, ?)', (product, quantity))
        
        if operation == 'remove_from_stock':
            cursor.execute('INSERT INTO output_stock (product, quantity) VALUES (?, ?)', (product, quantity))

        self.rebalance_stock(product)

        self.db_connection.commit()
        self.load_db()
        self.stock_input.clear()

    def closeEvent(self, event):
        self.db_connection.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BannerStock()
    window.show()
    sys.exit(app.exec_())