# Requirements

### Required Python Packages

| Command                              | Description                                                                     |
|--------------------------------------|---------------------------------------------------------------------------------|
| `pip install Flask`                  | Installs the Flask framework.                                                   |
| `pip install mysql-connector-python` | Provides MySQL database connectivity.                                           |
| `pip install flask-session`          | Enables server-side session management.                                         |
| `pip install python-dotenv`          | Reads key-value pairs from a .env file and sets them as environment variables.  |
| `pip install iyzipay`                |                                                                                 |
| `pip install google-genai python-dotenv`                |                                                                                 |

### Environment Variables (.env) Setup

To keep the application secure, database credentials and secret keys are stored in a .env file.
Create a file named .env in the root directory of your project and fill it with your own credentials:

DB_HOST=localhost
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=food_delivery
FLASK_SECRET_KEY=YOUR_FLASK_SECRET_KEY
