import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from recommender_core import MovieLensRecommender

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

print("Initializing MovieLens Recommender Engine...")
rec = MovieLensRecommender()
print("Recommender Engine Ready!")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/presentation')
def presentation():
    return send_from_directory('static', 'presentation.html')

@app.route('/Images/<path:filename>')
def serve_images(filename):
    return send_from_directory('Images', filename)

@app.route('/MovieLens_Recommender_System.pptx')
def serve_pptx():
    return send_from_directory('.', 'MovieLens_Recommender_System.pptx', as_attachment=True)

@app.route('/api/stats')
def get_stats():
    return jsonify(rec.get_dataset_stats())

@app.route('/api/search')
def search_movies():
    query = request.args.get('q', '')
    limit = int(request.args.get('limit', 10))
    suggestions = rec.suggest_movie_names(query, limit=limit)
    return jsonify({'query': query, 'suggestions': suggestions})

@app.route('/api/knowledge')
def knowledge_recs():
    genre = request.args.get('genre', 'All')
    min_viewers = int(request.args.get('min_viewers', 250))
    min_rating = float(request.args.get('min_rating', 4.0))
    limit = int(request.args.get('limit', 12))
    res = rec.get_knowledge_recommendations(
        genre=genre,
        min_viewers=min_viewers,
        min_rating=min_rating,
        limit=limit
    )
    return jsonify(res)

@app.route('/api/knn/movie')
def knn_movie_recs():
    movie = request.args.get('movie', '')
    top_n = int(request.args.get('top_n', 10))
    if not movie:
        return jsonify({'error': 'Missing movie parameter'}), 400
    res = rec.get_knn_movie_recommendations(movie, top_n=top_n)
    return jsonify(res)

@app.route('/api/knn/user')
def knn_user_recs():
    user_id = request.args.get('user_id', type=int)
    similar_users = int(request.args.get('similar_users', 15))
    n_movies = int(request.args.get('n_movies', 12))
    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400
    res = rec.get_knn_user_recommendations(user_id, n_similar_users=similar_users, n_movies=n_movies)
    return jsonify(res)

@app.route('/api/svd/movie')
def svd_movie_recs():
    movie = request.args.get('movie', '')
    top_n = int(request.args.get('top_n', 10))
    if not movie:
        return jsonify({'error': 'Missing movie parameter'}), 400
    res = rec.get_svd_movie_recommendations(movie, top_n=top_n)
    return jsonify(res)

@app.route('/api/compare/movie')
def compare_movie_recs():
    movie = request.args.get('movie', '')
    top_n = int(request.args.get('top_n', 8))
    if not movie:
        return jsonify({'error': 'Missing movie parameter'}), 400
    knn_res = rec.get_knn_movie_recommendations(movie, top_n=top_n)
    svd_res = rec.get_svd_movie_recommendations(movie, top_n=top_n)
    return jsonify({
        'query_movie': knn_res.get('query_movie') or svd_res.get('query_movie') or movie,
        'knn': knn_res,
        'svd': svd_res
    })

@app.route('/api/dnn/user')
def dnn_user_recs():
    user_id = request.args.get('user_id', type=int)
    n_movies = int(request.args.get('n_movies', 12))
    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400
    res = rec.get_dnn_user_recommendations(user_id, n_movies=n_movies)
    return jsonify(res)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"Starting server on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
