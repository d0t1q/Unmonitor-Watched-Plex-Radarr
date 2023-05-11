import time
import requests
from plexapi.server import PlexServer
import xml.etree.ElementTree as ET


PLEX_SERVER_URL = "http://LOCALHOST:32400"  # Replace with your Plex server address
PLEX_API_TOKEN = "PLEXTOKEN"
PLEX_MOVIE_SECTION = "Movies"
PLEX_USERS_TO_MONITOR = ["user1","user2"]  # Add the Plex usernames to monitor here

RADARR_API_KEY = "RADARRKEY"
RADARR_HOST = "http://localhost:7878"  # Replace with your Radarr server address if different

INTERVAL = 10  # Time in seconds between checks

def get_plex_recently_watched_movies(plex_server):
    movies_section = plex_server.library.section(PLEX_MOVIE_SECTION)
    all_movies = movies_section.all()
    watched_movies = []

    accounts_url = f"{PLEX_SERVER_URL}/accounts?X-Plex-Token={PLEX_API_TOKEN}"
    accounts_response = requests.get(accounts_url)
    accounts_xml = ET.fromstring(accounts_response.text)
    all_users = {int(account.get("id")): account.get("name") for account in accounts_xml.findall("Account") if account.get("name")}

    monitored_users = {user_id: username for user_id, username in all_users.items() if username.lower() in [u.lower() for u in PLEX_USERS_TO_MONITOR]}
    print("Monitored Users:", monitored_users)

    for user_id, username in monitored_users.items():
        print(f"Checking recently watched movies for user {username} (ID: {user_id})")
        history_url = f"{PLEX_SERVER_URL}/status/sessions/history/all?user_id={user_id}&X-Plex-Token={PLEX_API_TOKEN}"
        history_response = requests.get(history_url)
        history_xml = ET.fromstring(history_response.text)
        watched_rating_keys = []
        for video in history_xml.findall(".//Video"):
            rating_key = video.attrib.get("ratingKey")
            if rating_key is not None:
                try:
                    watched_rating_keys.append(int(rating_key))
                except ValueError:
                    pass
        for movie in all_movies:
            movie_watched = movie.ratingKey in watched_rating_keys
            print(f"Movie: {movie.title}, Watched by user {username}: {movie_watched}")
            if movie_watched and movie not in watched_movies:
                watched_movies.append(movie)
                print(f"Adding {movie.title} to the watched_movies list")

    return watched_movies



def find_radarr_movie(title):
    try:
        response = requests.get(f"{RADARR_HOST}/api/v3/movie", params={"apiKey": RADARR_API_KEY})
        response.raise_for_status()
        movies = response.json()

        for movie in movies:
            if movie["title"] == title:
                return movie
        return None
    except Exception as e:
        print(f"Error while fetching movie list from Radarr: {e}")
        return None

def unmonitor_radarr_movie(movie_id):
    try:
        print(f"Unmonitoring movie with ID {movie_id} in Radarr...")
        response = requests.get(f"{RADARR_HOST}/api/v3/movie/{movie_id}", params={"apiKey": RADARR_API_KEY})
        response.raise_for_status()
        movie = response.json()
        movie["monitored"] = False

        response = requests.put(f"{RADARR_HOST}/api/v3/movie", json=movie, params={"apiKey": RADARR_API_KEY})
        response.raise_for_status()
        print(f"Movie with ID {movie_id} successfully unmonitored in Radarr.")
        print("Press Enter to continue...")
        input()
    except Exception as e:
        print(f"Error while unmonitoring movie with ID {movie_id} in Radarr: {e}")

def main():
    print("Starting Plex-Radarr Unmonitor script...")
    plex_server = PlexServer(PLEX_SERVER_URL, PLEX_API_TOKEN)
    while True:
        print("Checking for recently watched movies...")
        watched_movies = get_plex_recently_watched_movies(plex_server)
        for movie in watched_movies:
            print(f"Found watched movie: {movie.title}")
            radarr_movie = find_radarr_movie(movie.title)
            if radarr_movie and radarr_movie["monitored"]:
                print(f"Unmonitoring {movie.title} in Radarr")
                unmonitor_radarr_movie(radarr_movie["id"])
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
