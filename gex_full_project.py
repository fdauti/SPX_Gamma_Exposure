import sys
import csv
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
                             QFileDialog, QLabel, QLineEdit, QCheckBox, QGroupBox, QStyledItemDelegate)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtCore import Qt, QRect

class GEXBarDelegate(QStyledItemDelegate):
    def __init__(self, max_value, parent=None):
        super().__init__(parent)
        self.max_value = max_value

    def paint(self, painter, option, index):
        value = index.data(Qt.ItemDataRole.UserRole)
        if value is None:
            return

        painter.save()

        # Calculate the width of the bar
        width = int(abs(value) / self.max_value * option.rect.width())
        
        # Determine color and position based on value
        if value >= 0:
            color = QColor(0, 180, 0)  # Darker green for positive
            rect = QRect(int(option.rect.right() - width), option.rect.y(), width, option.rect.height())
        else:
            color = QColor(255, 0, 0)  # Red for negative
            rect = QRect(int(option.rect.right() - width), option.rect.y(), width, option.rect.height())

        # Draw the bar
        painter.fillRect(rect, color)

        painter.restore()

class GEXAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPY Net GEX Analysis")
        self.setGeometry(100, 100, 1400, 800)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)
        self.setup_ui()

    def setup_ui(self):
        # Left side: Table and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Controls
        controls_layout = QHBoxLayout()
        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        self.spot_price_input = QLineEdit()
        self.spot_price_input.setPlaceholderText("Enter Spot Price")
        controls_layout.addWidget(self.load_button)
        controls_layout.addWidget(QLabel("Spot Price:"))
        controls_layout.addWidget(self.spot_price_input)
        left_layout.addLayout(controls_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["Strike", "GEX Bar", "Net GEX", "Abs GEX", "Total OI", "Call OI", "Put OI", "%", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        left_layout.addWidget(self.table)

        self.layout.addWidget(left_widget, 2)

        # Right side: Expiration date selection and additional data
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Max Pain Data Box
        max_pain_group = QGroupBox("Max Pain Data")
        max_pain_layout = QVBoxLayout(max_pain_group)
        self.max_pain_label = QLabel("Max Pain: N/A")
        self.max_pain_comparison_label = QLabel("Comparison: N/A")
        max_pain_layout.addWidget(self.max_pain_label)
        max_pain_layout.addWidget(self.max_pain_comparison_label)
        right_layout.addWidget(max_pain_group)

        # Additional data section
        additional_data_group = QGroupBox("Additional Data")
        additional_data_layout = QVBoxLayout(additional_data_group)
        self.put_call_ratio_label = QLabel("Put/Call Ratio: N/A")
        self.net_positive_gamma_label = QLabel("Net Positive Gamma: N/A")
        self.net_negative_gamma_label = QLabel("Net Negative Gamma: N/A")
        additional_data_layout.addWidget(self.put_call_ratio_label)
        additional_data_layout.addWidget(self.net_positive_gamma_label)
        additional_data_layout.addWidget(self.net_negative_gamma_label)
        right_layout.addWidget(additional_data_group)

        # Expiration date selection
        right_layout.addWidget(QLabel("Included Expirations"))
        right_layout.addWidget(QLabel("Select which expirations to exclude from the data set then press submit."))
        self.expiration_group = QGroupBox()
        self.expiration_layout = QVBoxLayout(self.expiration_group)
        right_layout.addWidget(self.expiration_group)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.update_table)
        right_layout.addWidget(self.submit_button)

        right_layout.addStretch(1)
        self.layout.addWidget(right_widget, 1)

    def load_csv(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open CSV File", "", "CSV Files (*.csv)")
        if file_name:
            self.data = self.read_csv(file_name)
            self.populate_expiration_checkboxes()

    def read_csv(self, file_name):
        data = []

        def parse_float(value):
            value = (value or "").strip().replace(",", "")
            return float(value) if value else 0.0

        def parse_int(value):
            value = (value or "").strip().replace(",", "")
            return int(float(value)) if value else 0

        with open(file_name, 'r', encoding='utf-8-sig', newline='') as file:
            csv_reader = csv.reader(file)
            headers = None

            for row in csv_reader:
                if not row or not any(cell.strip() for cell in row):
                    continue

                if headers is None:
                    if "Expiration Date" in row:
                        headers = row
                    continue

                exp_date_idx = headers.index("Expiration Date")
                call_gamma_idx = headers.index("Gamma", 9)
                call_oi_idx = headers.index("Open Interest", 10)
                strike_idx = headers.index("Strike", 11)
                put_gamma_idx = headers.index("Gamma", 20)
                put_oi_idx = headers.index("Open Interest", 21)

                expiration = row[exp_date_idx] if exp_date_idx < len(row) else ""
                call_gamma = row[call_gamma_idx] if call_gamma_idx < len(row) else ""
                call_oi = row[call_oi_idx] if call_oi_idx < len(row) else ""
                strike = row[strike_idx] if strike_idx < len(row) else ""
                put_gamma = row[put_gamma_idx] if put_gamma_idx < len(row) else ""
                put_oi = row[put_oi_idx] if put_oi_idx < len(row) else ""

                data.append([
                    expiration,
                    str(parse_float(call_gamma)),
                    str(parse_int(call_oi)),
                    str(parse_float(strike)),
                    str(parse_float(put_gamma)),
                    str(parse_int(put_oi)),
                ])

        return data


    def populate_expiration_checkboxes(self):
        for i in reversed(range(self.expiration_layout.count())):
            self.expiration_layout.itemAt(i).widget().setParent(None)
        
        current_date = datetime.now().date()
        expirations = set(row[0] for row in self.data)
        sorted_expirations = sorted(expirations, key=lambda x: datetime.strptime(x, "%a %b %d %Y").date())
        
        for exp in sorted_expirations:
            exp_date = datetime.strptime(exp, "%a %b %d %Y").date()
            if exp_date >= current_date:
                checkbox = QCheckBox(exp)
                checkbox.setChecked(True)
                self.expiration_layout.addWidget(checkbox)

    def get_spot_price(self):
        value = self.spot_price_input.text().strip().replace(",", "")
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def update_table(self):
        if not hasattr(self, "data") or not self.data:
            self.table.setRowCount(0)
            return

        spot_price = self.get_spot_price()
        if spot_price is None:
            self.table.setRowCount(0)
            self.max_pain_label.setText("Max Pain: N/A")
            self.max_pain_comparison_label.setText("Comparison: N/A")
            self.put_call_ratio_label.setText("Put/Call Ratio: N/A")
            self.net_positive_gamma_label.setText("Net Positive Gamma: N/A")
            self.net_negative_gamma_label.setText("Net Negative Gamma: N/A")
            return

        selected_expirations = [cb.text() for cb in self.expiration_group.findChildren(QCheckBox) if cb.isChecked()]
        filtered_data = [row for row in self.data if row[0] in selected_expirations]
        gex_data = self.calculate_gex(filtered_data, spot_price)
        
        # Filter strikes within ±300 points of spot price
        min_strike = spot_price - 300
        max_strike = spot_price + 300
        filtered_gex_data = {k: v for k, v in gex_data.items() if min_strike <= k <= max_strike}
        
        self.populate_table(filtered_gex_data, spot_price)

    def calculate_gex(self, data, spot_price):
        gex_data = {}
        for row in data:
            expiration, call_gamma, call_oi, strike, put_gamma, put_oi = row
            strike = float(strike)
            call_gamma, put_gamma = float(call_gamma), float(put_gamma)
            call_oi, put_oi = int(call_oi), int(put_oi)
            call_gex = call_gamma * call_oi * spot_price * spot_price
            put_gex = put_gamma * put_oi * spot_price * spot_price * -1
            net_gex = call_gex + put_gex
            abs_gex = abs(call_gex) + abs(put_gex)

            if strike not in gex_data:
                gex_data[strike] = {'net_gex': 0, 'abs_gex': 0, 'total_oi': 0, 'call_oi': 0, 'put_oi': 0}

            gex_data[strike]['net_gex'] += net_gex
            gex_data[strike]['abs_gex'] += abs_gex
            gex_data[strike]['total_oi'] += call_oi + put_oi
            gex_data[strike]['call_oi'] += call_oi
            gex_data[strike]['put_oi'] += put_oi

        return gex_data

    def calculate_max_pain(self, gex_data):
        total_pain = {strike: 0 for strike in gex_data}
        for strike in gex_data:
            for option_strike, option_data in gex_data.items():
                call_pain = max(0, strike - option_strike) * option_data['call_oi']
                put_pain = max(0, option_strike - strike) * option_data['put_oi']
                total_pain[strike] += call_pain + put_pain
        return min(total_pain, key=total_pain.get)

    def calculate_put_call_ratio(self, gex_data):
        total_put_oi = sum(data['put_oi'] for data in gex_data.values())
        total_call_oi = sum(data['call_oi'] for data in gex_data.values())
        return total_put_oi / total_call_oi if total_call_oi != 0 else float('inf')

    def calculate_net_gamma(self, gex_data):
        positive_gamma = sum(data['net_gex'] for data in gex_data.values() if data['net_gex'] > 0)
        negative_gamma = sum(data['net_gex'] for data in gex_data.values() if data['net_gex'] < 0)
        return positive_gamma, negative_gamma

    def populate_table(self, gex_data, spot_price):
        self.table.setRowCount(0)
        all_strikes = sorted(gex_data.keys(), reverse=True)  # Sort strikes in descending order

        # Determine thresholds for highlighting
        highest_net_gex = sorted(all_strikes, key=lambda s: gex_data[s]['net_gex'], reverse=True)[:2]
        lowest_net_gex = sorted(all_strikes, key=lambda s: gex_data[s]['net_gex'])[:2]
        highest_abs_gex = sorted(all_strikes, key=lambda s: gex_data[s]['abs_gex'], reverse=True)[:2]
        highest_call_oi = max(all_strikes, key=lambda s: gex_data[s]['call_oi'])
        highest_put_oi = max(all_strikes, key=lambda s: gex_data[s]['put_oi'])
        highest_total_oi = max(all_strikes, key=lambda s: gex_data[s]['total_oi'])

        # Calculate OI thresholds for gray shading (top 10%)
        top_percentage = 0.1
        num_to_highlight = max(1, int(len(all_strikes) * top_percentage))
        top_oi_strikes = sorted(all_strikes, key=lambda s: gex_data[s]['total_oi'], reverse=True)[:num_to_highlight]
        top_call_oi_strikes = sorted(all_strikes, key=lambda s: gex_data[s]['call_oi'], reverse=True)[:num_to_highlight]
        top_put_oi_strikes = sorted(all_strikes, key=lambda s: gex_data[s]['put_oi'], reverse=True)[:num_to_highlight]

        # Find the maximum absolute GEX value for scaling
        max_abs_gex = max(abs(data['net_gex']) for data in gex_data.values())
        max_abs_gex = max(max_abs_gex, 1)  # Ensure it's never zero

        closest_strike = min(all_strikes, key=lambda x: abs(x - spot_price))

        for strike, data in sorted(gex_data.items(), reverse=True):  # Sort items in descending order
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            strike_item = QTableWidgetItem(f"{strike:.2f}")
            if strike == closest_strike:
                strike_item.setBackground(QColor(255, 255, 0))  # Yellow background for closest strike
            self.table.setItem(row_position, 0, strike_item)

            # Add GEX bar
            gex_bar_item = QTableWidgetItem()
            gex_bar_item.setData(Qt.ItemDataRole.UserRole, data['net_gex'])
            self.table.setItem(row_position, 1, gex_bar_item)

            self.table.setItem(row_position, 2, QTableWidgetItem(f"{data['net_gex']:,.0f}"))
            self.table.setItem(row_position, 3, QTableWidgetItem(f"{data['abs_gex']:,.0f}"))
            self.table.setItem(row_position, 4, QTableWidgetItem(f"{data['total_oi']:,}"))
            self.table.setItem(row_position, 5, QTableWidgetItem(f"{data['call_oi']:,}"))
            self.table.setItem(row_position, 6, QTableWidgetItem(f"{data['put_oi']:,}"))

            percentage = (data['net_gex'] / data['abs_gex']) * 100 if data['abs_gex'] != 0 else 0
            self.table.setItem(row_position, 7, QTableWidgetItem(f"{percentage:.2f}%"))

            # Highlighting
            if strike in highest_net_gex:
                color = QColor(0, 100, 0) if strike == highest_net_gex[0] else QColor(0, 150, 0)
                self.table.item(row_position, 2).setBackground(color)
                self.table.item(row_position, 2).setForeground(QColor(255, 255, 255))  # White text
            elif strike in lowest_net_gex:
                color = QColor(100, 0, 0) if strike == lowest_net_gex[0] else QColor(150, 0, 0)
                self.table.item(row_position, 2).setBackground(color)
                self.table.item(row_position, 2).setForeground(QColor(255, 255, 255))  # White text


            if strike == highest_abs_gex[0]:
                color = QColor(0, 0, 150)
                self.table.item(row_position, 3).setBackground(color)
                self.table.item(row_position, 3).setForeground(QColor(255, 255, 255))  # White text
            elif strike == highest_abs_gex[1]:
                color = QColor(0, 0, 200)
                self.table.item(row_position, 3).setBackground(color)
                self.table.item(row_position, 3).setForeground(QColor(255, 255, 255))  # White text

            if strike == highest_call_oi:
                self.table.item(row_position, 5).setText(f"{data['call_oi']:,} \u25CF")
                self.table.item(row_position, 5).setForeground(QColor(0, 255, 0))  # Green text

            if strike == highest_put_oi:
                self.table.item(row_position, 6).setText(f"{data['put_oi']:,} \u25CF")
                self.table.item(row_position, 6).setForeground(QColor(255, 0, 0))  # Red text

            if strike == highest_total_oi:
                self.table.item(row_position, 4).setText(f"{data['total_oi']:,} \u25CF")
                self.table.item(row_position, 4).setForeground(QColor(0, 0, 255))  # Blue text

        # Gray shading based on OI
            if strike in top_oi_strikes:
                gray_shade = int(255 * (1 - (top_oi_strikes.index(strike) / len(top_oi_strikes))))
                gray_color = QColor(gray_shade, gray_shade, gray_shade)
                self.table.item(row_position, 4).setBackground(gray_color)

            if strike in top_call_oi_strikes:
                gray_shade = int(255 * (1 - (top_call_oi_strikes.index(strike) / len(top_call_oi_strikes))))
                gray_color = QColor(gray_shade, gray_shade, gray_shade)
                self.table.item(row_position, 5).setBackground(gray_color)

            if strike in top_put_oi_strikes:
                gray_shade = int(255 * (1 - (top_put_oi_strikes.index(strike) / len(top_put_oi_strikes))))
                gray_color = QColor(gray_shade, gray_shade, gray_shade)
                self.table.item(row_position, 6).setBackground(gray_color)

    # Set custom delegate for GEX bar column
        gex_bar_delegate = GEXBarDelegate(max_abs_gex, self.table)
        self.table.setItemDelegateForColumn(1, gex_bar_delegate)

    # Make the GEX bar column wider
        self.table.setColumnWidth(1, 200)  # Adjust the width as needed

    # Calculate and display Max Pain
        max_pain_price = self.calculate_max_pain(gex_data)
        self.max_pain_label.setText(f"Max Pain: ${max_pain_price:.2f}")
        difference = spot_price - max_pain_price
        comparison = f"Spot is ${abs(difference):.2f} {'above' if difference > 0 else 'below'} max pain"
        self.max_pain_comparison_label.setText(f"Comparison: {comparison}")

    # Calculate and display additional data
        put_call_ratio = self.calculate_put_call_ratio(gex_data)
        net_positive_gamma, net_negative_gamma = self.calculate_net_gamma(gex_data)

        self.put_call_ratio_label.setText(f"Put/Call Ratio: {put_call_ratio:.2f}")
        self.net_positive_gamma_label.setText(f"Net Positive Gamma: {net_positive_gamma:,.0f}")
        self.net_negative_gamma_label.setText(f"Net Negative Gamma: {net_negative_gamma:,.0f}")

    # Set colors for gamma labels
        self.net_positive_gamma_label.setStyleSheet("color: green;")
        self.net_negative_gamma_label.setStyleSheet("color: red;")

    # Scroll to the closest strike
        closest_strike_row = all_strikes.index(closest_strike)
        self.table.scrollToItem(self.table.item(closest_strike_row, 0), QTableWidget.ScrollHint.PositionAtCenter)

def calculate_max_pain(self, gex_data):
    total_pain = {strike: 0 for strike in gex_data}
    for strike in gex_data:
        for option_strike, option_data in gex_data.items():
            call_pain = max(0, strike - option_strike) * option_data['call_oi']
            put_pain = max(0, option_strike - strike) * option_data['put_oi']
            total_pain[strike] += call_pain + put_pain
    return min(total_pain, key=total_pain.get)

def calculate_put_call_ratio(self, gex_data):
    total_put_oi = sum(data['put_oi'] for data in gex_data.values())
    total_call_oi = sum(data['call_oi'] for data in gex_data.values())
    return total_put_oi / total_call_oi if total_call_oi != 0 else float('inf')

def calculate_net_gamma(self, gex_data):
    positive_gamma = sum(data['net_gex'] for data in gex_data.values() if data['net_gex'] > 0)
    negative_gamma = sum(data['net_gex'] for data in gex_data.values() if data['net_gex'] < 0)
    return positive_gamma, negative_gamma

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GEXAnalysisApp()
    window.show()
    sys.exit(app.exec())
