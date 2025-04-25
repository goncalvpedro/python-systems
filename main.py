import sys
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
    QMessageBox, QGridLayout
)
from sqlalchemy import func
from datetime import datetime as dt

from database import Session, InputStock, OutputStock, BalancedStock

class BannerStock(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Estoque Banner")
        self.setGeometry(200, 100, 900, 700)
        self.session = Session()
        self.products = self.get_products()
        self.initUI()

    def get_products(self):
        return ['-', '11 10.5-19', '11 10.5-21', '11 10.5K-25', '11 10.5E-16', '11 10.5E-18',
                '5S 8-16.5', '5S 8A -19', '5S 8A-16.5', '5S 8E-18', '5S 8K-17.5', '5S 8M -16',
                '5S 8N-13', '6174 N (LTS)', '9 10-16', '9 10-18-5', '9 10-19', '9 10-21',
                '9 95SP-14-4', '9 9KS-17.5', '9 9LS-13.5', '9 9S - 12',
                'Manta BLSB 5590 - 680 X 0.9 mm', 'Manta BLSB 5590 - 670 x 1.2 mm',
                'Manta BLSB 5590 - 515 X 1.4 mm', 'Manta BLSB 5590 - 515 X 0.9 mm',
                'Tecido Calandrado Camaçari']

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        grid = QGridLayout()

        self.product_dropdown = QComboBox()
        self.product_dropdown.addItems(self.products)
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("Digite a quantidade")

        self.add_button = QPushButton("Adicionar Estoque")
        self.remove_button = QPushButton("Remover Estoque")
        self.export_button = QPushButton("Exportar CSV")

        self.add_button.clicked.connect(lambda: self.modify_stock("entrada"))
        self.remove_button.clicked.connect(lambda: self.modify_stock("saida"))
        self.export_button.clicked.connect(self.export_to_csv)

        grid.addWidget(QLabel("Produto:"), 0, 0)
        grid.addWidget(self.product_dropdown, 0, 1)
        grid.addWidget(QLabel("Quantidade:"), 1, 0)
        grid.addWidget(self.stock_input, 1, 1)
        grid.addWidget(self.add_button, 2, 0)
        grid.addWidget(self.remove_button, 2, 1)
        grid.addWidget(self.export_button, 3, 0, 1, 2)

        layout.addLayout(grid)

        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(2)
        self.stock_table.setHorizontalHeaderLabels(['Produto', 'Saldo'])
        layout.addWidget(QLabel("Estoque Atual"))
        layout.addWidget(self.stock_table)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(4)
        self.transactions_table.setHorizontalHeaderLabels(['Produto', 'Quantidade', 'Data', 'Tipo'])
        layout.addWidget(QLabel("Movimentações"))
        layout.addWidget(self.transactions_table)

        central_widget.setLayout(layout)

        self.load_stock()
        self.load_transactions()

    def modify_stock(self, tipo):
        product = self.product_dropdown.currentText()
        if product == '-':
            return

        try:
            quantity = int(self.stock_input.text())
        except ValueError:
            QMessageBox.warning(self, "Erro", "Quantidade inválida")
            return

        if tipo == "entrada":
            self.session.add(InputStock(product=product, quantity=quantity))
        else:
            self.session.add(OutputStock(product=product, quantity=quantity))

        self.session.commit()
        self.update_balance(product)
        self.load_stock()
        self.load_transactions()
        self.stock_input.clear()

    def update_balance(self, product):
        entrada = self.session.query(func.sum(InputStock.quantity)).filter_by(product=product).scalar() or 0
        saida = self.session.query(func.sum(OutputStock.quantity)).filter_by(product=product).scalar() or 0
        saldo = entrada - saida

        existing = self.session.query(BalancedStock).filter_by(product=product).first()
        if existing:
            existing.current_stock = saldo
        else:
            self.session.add(BalancedStock(product=product, current_stock=saldo))

        self.session.commit()

    def load_stock(self):
        self.stock_table.setRowCount(0)
        stocks = self.session.query(BalancedStock).order_by(BalancedStock.product).filter(BalancedStock.current_stock != 0 ).all()

        self.stock_table.setRowCount(len(stocks))
        for i, item in enumerate(stocks):
            self.stock_table.setItem(i, 0, QTableWidgetItem(item.product))
            self.stock_table.setItem(i, 1, QTableWidgetItem(f"{item.current_stock} bobinas"))

        self.stock_table.resizeColumnsToContents()

    def load_transactions(self):
        self.transactions_table.setRowCount(0)
        entradas = self.session.query(InputStock.product, InputStock.quantity, InputStock.updated_at).all()
        saidas = self.session.query(OutputStock.product, OutputStock.quantity, OutputStock.updated_at).all()

        trans = [(p, q, d, "Entrada") for p, q, d in entradas] + [(p, q, d, "Saída") for p, q, d in saidas]
        trans.sort(key=lambda x: x[2], reverse=True)

        self.transactions_table.setRowCount(len(trans))
        for i, (produto, quantidade, data, tipo) in enumerate(trans):
            self.transactions_table.setItem(i, 0, QTableWidgetItem(produto))
            self.transactions_table.setItem(i, 1, QTableWidgetItem(str(quantidade)))
            self.transactions_table.setItem(i, 2, QTableWidgetItem(str(data)))
            self.transactions_table.setItem(i, 3, QTableWidgetItem(tipo))

        self.transactions_table.resizeColumnsToContents()

    def export_to_csv(self):
        entradas = self.session.query(InputStock.product, InputStock.quantity, InputStock.updated_at).all()
        saidas = self.session.query(OutputStock.product, OutputStock.quantity, OutputStock.updated_at).all()
        data = [(p, q, d, "Entrada") for p, q, d in entradas] + [(p, q, d, "Saída") for p, q, d in saidas]

        df = pd.DataFrame(data, columns=["Produto", "Quantidade", "Data", "Tipo"])

        directory = "Dados Estoque"
        filename = f"{directory}/stock_{dt.now().strftime('%Y%m%d_%H%M')}.csv"

        # Cria o diretório se não existir
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        df.to_csv(filename, index=False)

        QMessageBox.information(self, "Exportado", f"Exportado como {filename}")

    def closeEvent(self, event):
        self.session.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BannerStock()
    window.show()
    sys.exit(app.exec_())
