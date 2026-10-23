#!/usr/bin/env python3
"""
Interactive Terminal CLI for MovieLens Recommender System
"""
import sys
from recommender_core import MovieLensRecommender

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def main():
    print_header("🎬 MovieLens Recommender System (100K Dataset)")
    print("Loading datasets and training KNN/SVD models...")
    rec = MovieLensRecommender()
    stats = rec.get_dataset_stats()
    print(f"✓ Loaded {stats['total_ratings']:,} ratings from {stats['total_users']:,} users across {stats['total_movies']:,} movies!\n")

    while True:
        print("\nChoose an option:")
        print("1. 🌟 Knowledge-Based Recommendations (Cold Start / Genre Explorer)")
        print("2. 🎬 Item-Based Collaborative Filtering (KNN Movie Similarity)")
        print("3. 👤 User-Based Collaborative Filtering (KNN Peer Recommendations)")
        print("4. 🧬 Matrix Factorization using SVD (Latent Feature Similarities)")
        print("5. 🧠 Latent / Neural User Recommendations")
        print("6. 🔍 Autocomplete Movie Name Search")
        print("0. 🚪 Exit")

        choice = input("\nEnter choice [0-6]: ").strip()
        if choice == '0':
            print("Goodbye!")
            break
        elif choice == '1':
            print("\nAvailable genres: " + ", ".join(rec.genre_list))
            genre = input("Enter genre (or press Enter for All): ").strip()
            if not genre:
                genre = 'All'
            res = rec.get_knowledge_recommendations(genre=genre, limit=10)
            print_header(f"Top Rated Popular Movies ({genre})")
            for i, m in enumerate(res['top_popular_rated'], 1):
                print(f"{i:2d}. {m['title']} | ★ {m['avg_rating']:.2f} | {m['watch_count']} views | {', '.join(m['genres'][:3])}")

        elif choice == '2':
            movie = input("Enter movie name (e.g. Star Wars, Toy Story): ").strip()
            res = rec.get_knn_movie_recommendations(movie, top_n=10)
            if 'error' in res:
                print(f"⚠️ {res['error']}. Suggestions: {res.get('suggestions', [])}")
            else:
                print_header(f"Movies Similar to '{res['query_movie']}' (KNN Cosine)")
                for i, m in enumerate(res['recommendations'], 1):
                    print(f"{i:2d}. {m['title']} | Match: {m['similarity']}% | ★ {m['avg_rating']} | {', '.join(m['genres'][:3])}")

        elif choice == '3':
            user_input = input("Enter user ID (1 - 943) [default: 307]: ").strip()
            uid = int(user_input) if user_input.isdigit() else 307
            res = rec.get_knn_user_recommendations(uid, n_similar_users=15, n_movies=10)
            if 'error' in res:
                print(f"⚠️ {res['error']}")
            else:
                print(f"\nTop watched movies by User {uid}:")
                for h in res['user_history'][:5]:
                    print(f" • {h['title']} (Rated: ★ {h['rating']})")
                print(f"\nTop Similar Peers found: {', '.join(str(p['user_id']) for p in res['similar_peers'])}")
                print_header(f"Personalized Recommendations for User {uid} (KNN)")
                for i, m in enumerate(res['recommendations'], 1):
                    print(f"{i:2d}. {m['title']} | Score: {m['predicted_score']} | ★ {m['avg_rating']} | {', '.join(m['genres'][:3])}")

        elif choice == '4':
            movie = input("Enter movie name (e.g. Star Wars, 101 Dalmatians): ").strip()
            res = rec.get_svd_movie_recommendations(movie, top_n=10)
            if 'error' in res:
                print(f"⚠️ {res['error']}. Suggestions: {res.get('suggestions', [])}")
            else:
                print_header(f"Latent Factor Similar Movies for '{res['query_movie']}' (SVD)")
                for i, m in enumerate(res['recommendations'], 1):
                    print(f"{i:2d}. {m['title']} | Latent Match: {m['similarity']}% | ★ {m['avg_rating']}")

        elif choice == '5':
            user_input = input("Enter user ID (1 - 943) [default: 307]: ").strip()
            uid = int(user_input) if user_input.isdigit() else 307
            res = rec.get_dnn_user_recommendations(uid, n_movies=10)
            if 'error' in res:
                print(f"⚠️ {res['error']}")
            else:
                print_header(f"Neural/Latent Predicted Movies for User {uid}")
                for i, m in enumerate(res['recommendations'], 1):
                    print(f"{i:2d}. {m['title']} | Predicted Rating: ★ {m['predicted_rating']} | {', '.join(m['genres'][:3])}")

        elif choice == '6':
            prefix = input("Enter search query: ").strip()
            matches = rec.suggest_movie_names(prefix, limit=10)
            print(f"Matches for '{prefix}':")
            for m in matches:
                print(f" • {m}")

if __name__ == '__main__':
    main()
