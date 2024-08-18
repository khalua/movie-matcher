# populate_db.py
from app import app, db, Movie
import random

# Sample movie data
sample_movies = [
    {
        "title": "The Shawshank Redemption",
        "poster": "https://m.media-amazon.com/images/M/MV5BNDE3ODcxYzMtY2YzZC00NmNlLWJiNDMtZDViZWM2MzIxZDYwXkEyXkFqcGdeQXVyNjAwNDUxODI@._V1_SX300.jpg",
        "description": "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
        "genre": "Drama",
        "rating": "9.3",
        "length": "142 min",
        "starring": "Tim Robbins, Morgan Freeman"
    },
    {
        "title": "The Godfather",
        "poster": "https://m.media-amazon.com/images/M/MV5BM2MyNjYxNmUtYTAwNi00MTYxLWJmNWYtYzZlODY3ZTk3OTFlXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX300.jpg",
        "description": "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.",
        "genre": "Crime, Drama",
        "rating": "9.2",
        "length": "175 min",
        "starring": "Marlon Brando, Al Pacino"
    },
    {
        "title": "Pulp Fiction",
        "poster": "https://m.media-amazon.com/images/M/MV5BNGNhMDIzZTUtNTBlZi00MTRlLWFjM2ItYzViMjE3YzI5MjljXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX300.jpg",
        "description": "The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.",
        "genre": "Crime, Drama",
        "rating": "8.9",
        "length": "154 min",
        "starring": "John Travolta, Uma Thurman"
    },
    {
        "title": "The Dark Knight",
        "poster": "https://m.media-amazon.com/images/M/MV5BMTMxNTMwODM0NF5BMl5BanBnXkFtZTcwODAyMTk2Mw@@._V1_SX300.jpg",
        "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.",
        "genre": "Action, Crime, Drama",
        "rating": "9.0",
        "length": "152 min",
        "starring": "Christian Bale, Heath Ledger"
    },
    {
        "title": "Forrest Gump",
        "poster": "https://m.media-amazon.com/images/M/MV5BNWIwODRlZTUtY2U3ZS00Yzg1LWJhNzYtMmZiYmEyNmU1NjMzXkEyXkFqcGdeQXVyMTQxNzMzNDI@._V1_SX300.jpg",
        "description": "The presidencies of Kennedy and Johnson, the Vietnam War, the Watergate scandal and other historical events unfold from the perspective of an Alabama man with an IQ of 75, whose only desire is to be reunited with his childhood sweetheart.",
        "genre": "Drama, Romance",
        "rating": "8.8",
        "length": "142 min",
        "starring": "Tom Hanks, Robin Wright"
    }
]

def populate_movies():
    with app.app_context():
        # Clear existing movies
        Movie.query.delete()

        # Add sample movies
        for movie_data in sample_movies:
            movie = Movie(**movie_data)
            db.session.add(movie)

        # Commit the changes
        db.session.commit()

        print(f"Added {len(sample_movies)} sample movies to the database.")

if __name__ == "__main__":
    populate_movies()