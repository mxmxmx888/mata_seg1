# Team Rose-4 Small Group Project

## Team members
The members of the team are:
- Maksym Byelko
- Ayan Mamun
- Tunjay Seyidali
- Amir Guliyev

## Project structure
The project is called `Recipi`.

## Deployed version of the application
The deployed version of the application can be found here: **[amirrza777.pythonanywhere.com](amirrza777.pythonanywhere.com)**

To access admin panel at amirrza777.pythonanywhere.com/admin , you can use log-in details below:

username: admin
password: admin

To acces one user with random credentials, you can use log-in details below:

username = demo123
email = demo@example.com
password = strong-pass-123


## Installation instructions

To install the software and use it in your local development environment, you must first set up and activate a local development environment. The project source code has been developed using **Python 3.14**, so you are recommended to use the same version.

### 1) Clone the repository and set up the virtual environment

From the root of the project:

```bash
python3.14 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

If your system does not have `python3.14` installed, replace `python3.14` with `python3` or `python`, provided it is a compatible version.

### 2) Install dependencies

```bash
pip3 install -r requirements.txt
```

### 3) Add Firebase configuration

This project requires a Firebase credentials file to function correctly.

Download the `firebase-service-account.json` file with the link provided below and insert it into the project folder:

https://drive.google.com/file/d/1fGG9TzHvjuwnhQcZMxo3Z3FPEWhR7ySM/view?usp=sharing

### 4) Configure environment variables

This project requires a `.env` file in the root directory (same level as `manage.py`) to handle configuration and secrets.

Download a file named `.env` using the link below (don't forget to change path to the firebase-service-account.json file to your local path):

https://drive.google.com/file/d/16rPEIwZ_0FrhqSk1wZ0VFP3Ahpru8uov/view?usp=sharing

### 5) Set up the database

Migrate the database schema:

```bash
python3 manage.py migrate
```

Seed the development database with initial data:

```bash
python3 manage.py seed
```

Optional: if you later want to remove the seeded sample data (non-staff users, etc.), run `python3 manage.py unseed`.

### 6) Create a superuser (for admin access)

To access the admin panel and configure social authentication, create a superuser account:

```bash
python3 manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

### 7) Run the application

Start the local development server:

```bash
python3 manage.py runserver
```

You can now access the application at:
- `http://127.0.0.1:8000/`

---

## 8) Admin panel & social authentication setup

To make Google Login work locally, you must configure the Django Admin panel to match your settings.

### Log in to the admin panel
1. Navigate to:
   - `http://127.0.0.1:8000/admin/`
2. Log in with the superuser credentials you created in Step 6.

### Verify site configuration
1. Under the **Sites** section, click **Sites**.
2. There should be an entry for your local domain (e.g., `127.0.0.1:8000` or `localhost:8000`).
   - If it lists `example.com`, click it and change both **Domain name** and **Display name** to `127.0.0.1:8000`.
3. **Important:** Note the ID of this site object in the URL  
   - Example: `/admin/sites/site/2/change/` means the ID is `2`.
4. Open `recipify/settings.py` and ensure the `SITE_ID` variable matches this number.
   - Example: `SITE_ID = 2`

### Add a social application (Google)
1. Return to the Admin home.
2. Under **Social Accounts**, click **Social applications**.
3. Click **Add social application** (top right).
4. Fill in:
   - **Provider:** Google
   - **Name:** Recipify
   - **Client id:** the `GOOGLE_CLIENT_ID` from `.env`
   - **Secret key:** the `GOOGLE_CLIENT_SECRET` from `.env`
5. Under **Sites**:
   - In “Available sites”, select your site (e.g., `127.0.0.1:8000`)
   - Click the arrow to move it to “Chosen sites”
6. Click **Save**.

---

### 9) Testing

Before starting testing make sure to install npm in repository root (used for JS testing) using this command:

```bash
npm install
```

Run all tests with:

```bash
npm test -- --coverage && python -m coverage run manage.py test && python -m coverage report
```

## Sources / technologies used

The packages used by this application are specified in `requirements.txt`. Key technologies and assets include:

- **Django Framework:** Backend web framework
- **Firebase Admin SDK:** Used for authentication and backend services
- **Bootstrap 5:** Frontend framework for responsive design
- **Bootstrap Icons:** Icon library
- **Google Fonts:** "Rethink Sans" font family
- **Local Assets:** Custom font ("Awesome Serif") located in the `static` directory
