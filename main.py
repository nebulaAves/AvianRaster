import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QWidget, QComboBox, QListWidget, QListWidgetItem,
    QHBoxLayout, QSizePolicy, QLineEdit, QScrollArea, QTextEdit, QStatusBar
)
from PyQt5.QtGui import QPixmap, QColor, QImage
from PyQt5.QtCore import Qt
from PIL import Image
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

class ColorWidgetItem(QWidget):
    def __init__(self, percentage, rgb_color):
        super().__init__()
        self.percentage = percentage
        self.rgb_color = rgb_color
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setAlignment(Qt.AlignLeft)  # Align widgets to the left

        # Display color as a small square
        color_label = QLabel()
        color_pixmap = QPixmap(30, 30)
        color_pixmap.fill(QColor(*self.rgb_color))
        color_label.setPixmap(color_pixmap)
        layout.addWidget(color_label)

        # Display percentage and RGB values
        text_label = QLabel(f"Percentage: {self.percentage:.2f}% RGB: {self.rgb_color}")
        layout.addWidget(text_label)

        # Dropdown for terrain type
        self.terrain_dropdown = QComboBox()
        self.terrain_dropdown.addItem("Select terrain type")
        terrains = [
            "Field", "Group of trees, bushes", "Grassland", "Water bodies", "Bogs",
            "Nutrient-poor grassland", "Pre-forest", "Mixed forest", "Deciduous forest",
            "Coniferous forest", "Settlements"
        ]
        self.terrain_dropdown.addItems(terrains)
        layout.addWidget(self.terrain_dropdown)

        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        self.setMinimumHeight(40)  # Adjust height as needed
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        return self.minimumSizeHint()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AvianRaster")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Create a scroll area for the entire main window content
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.central_widget.setLayout(QVBoxLayout(self.central_widget))
        self.central_widget.layout().addWidget(self.scroll_area)

        # Create a widget to contain the main layout
        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)

        self.layout = QVBoxLayout(self.scroll_content)

        self.label = QLabel("Choose an image or PDF file:")
        self.layout.addWidget(self.label)

        self.file_button = QPushButton("Choose File")
        self.file_button.clicked.connect(self.choose_file)
        self.layout.addWidget(self.file_button)

        self.image_label = QLabel()
        self.layout.addWidget(self.image_label)

        self.area_size_label = QLabel("Square Area Size (in hectares):")
        self.layout.addWidget(self.area_size_label)

        self.area_size_input = QLineEdit()
        self.layout.addWidget(self.area_size_input)

        self.number_label = QLabel("Number:")
        self.layout.addWidget(self.number_label)

        self.number_input = QLineEdit()
        self.layout.addWidget(self.number_input)

        self.species_label = QLabel("Species in Area:")
        self.layout.addWidget(self.species_label)

        # Species in Area dropdown
        self.species_dropdown = QComboBox()
        self.species_dropdown.addItem("Select species")
        terrains = [
            "Field", "Group of trees, bushes", "Grassland", "Water bodies", "Bogs",
            "Nutrient-poor grassland", "Pre-forest", "Mixed forest", "Deciduous forest",
            "Coniferous forest", "Settlements"
        ]
        self.species_dropdown.addItems(terrains)
        self.layout.addWidget(self.species_dropdown)

        # Create a scroll area for color entries
        self.color_scroll_area = QScrollArea()
        self.color_scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.color_scroll_area)

        # Create a list widget for color entries
        self.color_list = QListWidget()
        self.color_scroll_area.setWidget(self.color_list)

        # Calculate button with bird emoji
        self.calculate_button = QPushButton("Calculate 🐦")
        self.calculate_button.clicked.connect(self.calculate)
        self.layout.addWidget(self.calculate_button)

        # Output labels
        self.habitat_label = QLabel("Habitat: ")
        self.layout.addWidget(self.habitat_label)
        self.birdcount_label = QLabel("Birdcount: ")
        self.layout.addWidget(self.birdcount_label)

        # Console widget for status messages
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.layout.addWidget(self.console)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def choose_file(self):
        self.clear_previous_results()
        self.status_bar.showMessage("Choosing file...")
        file_dialog = QFileDialog()
        filepath, _ = file_dialog.getOpenFileName(self, "Choose File", "", "Image Files (*.png *.jpg *.jpeg *.pdf)")

        if filepath:
            # Load image and resize if needed
            self.status_bar.showMessage(f"Loading file: {filepath}")
            img = Image.open(filepath)
            img = self.resize_image(img)  # Resize image if it's too large

            # Convert Pillow Image to QPixmap
            qimage = self.pil_image_to_qimage(img)
            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)
            self.image_label.setAlignment(Qt.AlignCenter)

            # Calculate color percentages and display
            self.status_bar.showMessage("Calculating color percentages...")
            colors = self.calculate_color_percentages(img)
            self.display_color_entries(colors)

            self.status_bar.showMessage("File loaded and processed successfully.", 3000)  # 3 seconds duration

    def resize_image(self, img, max_size=1024):
        # Resize image if it's larger than max_size x max_size
        width, height = img.size
        if width > max_size or height > max_size:
            scale = min(max_size / width, max_size / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.ANTIALIAS)
        return img

    def pil_image_to_qimage(self, pil_img):
        image = pil_img.convert("RGBA").tobytes("raw", "RGBA")
        qimage = QImage(image, pil_img.size[0], pil_img.size[1], QImage.Format_ARGB32)
        return qimage

    def calculate_color_percentages(self, img):
        def process_image_part(image_part):
            color_data = list(image_part.getdata())
            color_counts = Counter(color_data)
            return color_counts

        width, height = img.size
        piece_height = height // 10

        # Create a ThreadPoolExecutor to process image parts in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                # Calculate the coordinates of the piece
                top = i * piece_height
                bottom = (i + 1) * piece_height if i < 9 else height
                image_part = img.crop((0, top, width, bottom))
                futures.append(executor.submit(process_image_part, image_part))

            # Collect the results
            color_counts_list = [future.result() for future in futures]

        # Combine the color counts from all parts
        combined_color_counts = Counter()
        for color_counts in color_counts_list:
            combined_color_counts.update(color_counts)

        # Calculate the percentages
        total_pixels = sum(combined_color_counts.values())
        colors = [
            (count / total_pixels * 100, color)
            for color, count in combined_color_counts.items()
        ]

        # Sort colors by percentage (descending)
        colors.sort(reverse=True, key=lambda x: x[0])

        return colors

    def display_color_entries(self, colors):
        self.color_list.clear()
        for percentage, rgb_color in colors:
            item = QListWidgetItem(self.color_list)
            widget = ColorWidgetItem(percentage, rgb_color)
            item.setSizeHint(widget.sizeHint())
            self.color_list.addItem(item)
            self.color_list.setItemWidget(item, widget)

    def calculate(self):
        try:
            area_size = float(self.area_size_input.text())
            number = int(self.number_input.text())
            selected_species = self.species_dropdown.currentText()

            if selected_species == "Select species":
                raise ValueError("Please select a species")

            # Find the selected color percentage
            selected_percentage = None
            for widget in self.get_color_widgets():
                if widget.terrain_dropdown.currentText() == selected_species:
                    selected_percentage = widget.percentage
                    break

            if selected_percentage is None:
                raise ValueError("Selected species not found in color list")

            habitat = (area_size / 100) * selected_percentage
            birdcount = habitat * number

            # Update labels with results, ensuring consistent formatting
            self.habitat_label.setText(f"Habitat: {habitat:.2f} hectares")
            self.birdcount_label.setText(f"Birdcount: {birdcount:.2f}")

            self.status_bar.showMessage("Calculation complete.")

        except ValueError as e:
            self.console.append(f"Error calculating habitat and birdcount: {e}")

    def get_color_widgets(self):
        widgets = []
        for i in range(self.color_list.count()):
            item = self.color_list.item(i)
            widget = self.color_list.itemWidget(item)
            if widget:
                widgets.append(widget)
        return widgets

    def clear_previous_results(self):
        # Clear previous results and reset labels
        self.image_label.clear()
        self.color_list.clear()
        self.habitat_label.setText("Habitat: ")
        self.birdcount_label.setText("Birdcount: ")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
