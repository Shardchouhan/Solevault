# SoleVault 👟

**SoleVault** is a premium sneaker e-commerce website designed for the Indian market. It features a responsive, modern UI built with Django and Bootstrap, catering to sneaker enthusiasts looking for verified, luxury sneakers.

## Features ✨

* **Responsive Design:** Fully mobile-friendly UI using Bootstrap 5.
* **Product Catalog:** Beautiful product display with images, categories, and dynamic price filtering.
* **Shopping Cart & Checkout:** Seamless add-to-cart experience.
* **Indian Market Ready:** Prices in ₹ INR with local payment mode displays.
* **Custom Filters:** Filter sneakers by newly arrived, popular, and precise price brackets.

## Technology Stack 🛠️

* **Backend:** Python 3, Django, SQLite (for development)
* **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript (ES6+), Bootstrap Icons

## Setup Instructions 🚀

To run this project locally on your machine, follow these steps:

1. **Navigate to the project directory:**
   Open your terminal and change into the project directory:
   ```bash
   cd SNEAKVAULT
   ```

2. **Create a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   Make sure you have Django and other required packages installed.
   ```bash
   pip install django pillow
   ```

4. **Run Database Migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Seed the Database with Sample Data:**
   We have included a custom management command to pre-load the database with products and images.
   ```bash
   python manage.py seed_data
   ```

6. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```

7. **View the Website:**
   Open your web browser and go to `http://127.0.0.1:8000/` to explore SoleVault!

## License 📄
This project is created for educational and portfolio purposes.
