from flask import Flask, render_template, request
import requests
import os
from google.cloud import secretmanager

app = Flask(__name__)

# Initialize the Secret Manager client
def get_secret(secret_name):
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')  # Ensure this environment variable is set
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")
        
        # Construct the resource name of the secret
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        
        # Access the secret version
        response = client.access_secret_version(name=name)
        
        # Return the decoded secret payload
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret {secret_name}: {e}")
        return None

# Retrieve API keys from Secret Manager
TMDB_API_KEY = get_secret('TMDB_API_KEY')
OMDB_API_KEY = get_secret('OMDB_API_KEY')

# Validate that the API keys were successfully retrieved
if not TMDB_API_KEY or not OMDB_API_KEY:
    raise ValueError("API keys could not be retrieved from Secret Manager.")

def get_latest_popular_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        popular_movies = data.get('results', [])[:10]  # Get the first 10 popular movies
        return popular_movies
    except requests.exceptions.RequestException as e:
        print(f"Error fetching popular movies: {e}")
        return []

def search_movies(movie_title):
    url = f"http://www.omdbapi.com/?s={movie_title}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error searching movies: {e}")
        return {"Response": "False", "Error": str(e)}

def get_movie_details_by_tmdb_id(tmdb_id):
    # Get the movie details from TMDb
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        tmdb_data = response.json()
        
        # Extract the IMDb ID from the TMDb data
        imdb_id = tmdb_data.get('imdb_id')
        
        # If IMDb ID is available, use it to get detailed information from OMDb
        if imdb_id:
            return get_movie_details(imdb_id)
        else:
            return tmdb_data  # If IMDb ID is not available, return the TMDb data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie details from TMDb: {e}")
        return {}

def get_movie_details(imdb_id):
    url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching movie details from OMDb: {e}")
        return {}

@app.route('/', methods=['GET', 'POST'])
def index():
    movies = []
    popular_movies = get_latest_popular_movies()  # Fetch latest popular movies

    if request.method == 'POST':
        movie_title = request.form.get('movie_title', '').strip()
        if movie_title:
            search_result = search_movies(movie_title)
            if search_result.get('Response') == 'True':
                movies = search_result.get('Search', [])
            else:
                movies = []
    
    return render_template('index.html', movies=movies, popular_movies=popular_movies)

@app.route('/movie/<string:tmdb_id>')
def movie_detail(tmdb_id):
    movie_details = get_movie_details_by_tmdb_id(tmdb_id)
    return render_template('movie_detail.html', movie=movie_details)

if __name__ == '__main__':
    app.run(debug=True)
