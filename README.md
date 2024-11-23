
## Setup

### Prerequisites

- Python 3.8+
- Django 4.2.15
- GitHub Personal Access Token

### Installation

1. Clone the repository:

    ```sh
    git clone <https://github.com/DefinitelyNotAnAssassin/GithubDev.git>
    cd backend
    ```

2. Create a virtual environment and activate it:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the dependencies:

    ```sh
    pip install -r requirements.txt
    ```

4. Set up environment variables:

    Create a `.env` file in the `backend` directory and add your GitHub Personal Access Token:

    ```env
    GITHUB_TOKEN="your_github_token"
    ```

5. Run database migrations:

    ```sh
    python manage.py migrate
    ```

6. Start the development server:

    ```sh
    python manage.py runserver
    ```

## API Endpoints

### Get Repositories

- **URL**: `/API/get_repo_info/<username>/`
- **Method**: `GET`
- **Description**: Fetches the repositories of a GitHub user.

### Get Extensions

- **URL**: `/API/getExtensions/`
- **Method**: `GET`
- **Description**: Fetches the default ignore extensions and directories.

### Get Leaderboard

- **URL**: `/API/getLeaderboard/`
- **Method**: `GET`
- **Description**: Fetches the leaderboard of users based on lines of code.

### Get Lines of Code

- **URL**: `/API/getLinesOfCode/<username>/`
- **Method**: `GET`
- **Description**: Fetches the lines of code for a GitHub user.

## Models

### UserRecord

- **Fields**:
  - `username`: `CharField`
  - `lines_of_code`: `IntegerField`
  - `lines_of_code_per_language`: `JSONField`
  - `repositories`: `JSONField`
  - `date_requested`: `DateTimeField`

## License

This project is licensed under the MIT License.