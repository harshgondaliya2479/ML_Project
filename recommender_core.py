import os
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors

class MovieLensRecommender:
    def __init__(self, data_dir='ml-100k'):
        self.data_dir = data_dir
        self.load_data()
        self.init_knn_models()
        self.init_svd_model()

    def load_data(self):
        # Column definitions
        u_data_cols = ['user id', 'movie id', 'rating', 'timestamp']
        genre_cols = [
            'unknown', 'Action', 'Adventure', 'Animation', "Children's", 'Comedy',
            'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror',
            'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western'
        ]
        u_item_cols = ['movie id', 'movie title', 'release date', 'video release date', 'IMDb URL'] + genre_cols

        # Load raw files
        self.ratings_df = pd.read_csv(
            os.path.join(self.data_dir, 'u.data'),
            sep='\t', header=None, names=u_data_cols
        )
        self.items_df = pd.read_csv(
            os.path.join(self.data_dir, 'u.item'),
            sep='|', header=None, names=u_item_cols, encoding='latin-1'
        )

        # Merge for combined ratings
        self.merged_df = pd.merge(
            self.ratings_df,
            self.items_df[['movie id', 'movie title'] + genre_cols],
            on='movie id',
            how='inner'
        )

        # Handle duplicates by averaging multiple ratings for same user and movie title
        self.refined_df = self.merged_df.groupby(['user id', 'movie title'], as_index=False)['rating'].mean()

        # Genre list
        self.genre_list = [g for g in genre_cols if g != 'unknown']

        # Precompute movie genre dictionary
        self.movie_genres_dict = {}
        for _, row in self.items_df.iterrows():
            m_title = row['movie title']
            g_active = [g for g in self.genre_list if row.get(g, 0) == 1]
            self.movie_genres_dict[m_title] = g_active

        # Precompute overall stats
        self.movie_stats = self.refined_df.groupby('movie title').agg(
            avg_rating=('rating', 'mean'),
            watch_count=('rating', 'count')
        ).reset_index()

        # Unique lists
        self.unique_movies = sorted(self.refined_df['movie title'].unique())
        self.unique_users = sorted(self.refined_df['user id'].unique())
        self.case_insensitive_movies = [m.lower() for m in self.unique_movies]
        self.movie_to_idx = {m: i for i, m in enumerate(self.unique_movies)}

    def init_knn_models(self):
        # 1. Movie-to-User matrix for Item-Based KNN
        self.movie_to_user_df = self.refined_df.pivot_table(
            index='movie title', columns='user id', values='rating'
        ).fillna(0)
        self.knn_movie_matrix = csr_matrix(self.movie_to_user_df.values)
        self.knn_movie_model = NearestNeighbors(metric='cosine', algorithm='brute')
        self.knn_movie_model.fit(self.knn_movie_matrix)
        self.knn_movie_names = list(self.movie_to_user_df.index)
        self.knn_movie_name_to_idx = {name: i for i, name in enumerate(self.knn_movie_names)}

        # 2. User-to-Movie matrix for User-Based KNN
        self.user_to_movie_df = self.refined_df.pivot_table(
            index='user id', columns='movie title', values='rating'
        ).fillna(0)
        self.knn_user_matrix = csr_matrix(self.user_to_movie_df.values)
        self.knn_user_model = NearestNeighbors(metric='cosine', algorithm='brute')
        self.knn_user_model.fit(self.knn_user_matrix)
        self.knn_user_ids = list(self.user_to_movie_df.index)
        self.user_id_to_idx = {uid: i for i, uid in enumerate(self.knn_user_ids)}

    def init_svd_model(self, k=50):
        # Utility matrix for SVD (movies as rows, users as columns)
        pivoted = self.refined_df.pivot_table(
            index='movie title', columns='user id', values='rating'
        )
        self.svd_movie_names = list(pivoted.index)
        self.svd_movie_to_idx = {m: i for i, m in enumerate(self.svd_movie_names)}
        
        matrix = pivoted.values
        # Mean rating per movie (ignoring NaNs)
        movie_means = np.nanmean(matrix, axis=1, keepdims=True)
        # Global fallback for any empty rows
        global_mean = np.nanmean(matrix)
        movie_means = np.where(np.isnan(movie_means), global_mean, movie_means)
        
        # Mean-centered & filled
        filled = np.where(np.isnan(matrix), movie_means, matrix)
        normalized = filled - movie_means
        
        # SVD: U represents movie latent space
        U, S, Vt = np.linalg.svd(normalized, full_matrices=False)
        self.svd_k = min(k, U.shape[1])
        # Movie representations in latent space
        self.movie_latent_matrix = U[:, :self.svd_k] * S[:self.svd_k]
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(self.movie_latent_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        self.movie_latent_normed = self.movie_latent_matrix / norms

        # Precompute full reconstructed ratings for DNN/Latent User scoring
        self.svd_reconstructed = (U[:, :self.svd_k] * S[:self.svd_k]) @ Vt[:self.svd_k, :] + movie_means
        self.svd_user_ids = list(pivoted.columns)
        self.svd_user_to_idx = {uid: i for i, uid in enumerate(self.svd_user_ids)}

    def get_dataset_stats(self):
        return {
            'total_ratings': len(self.ratings_df),
            'total_users': len(self.unique_users),
            'total_movies': len(self.unique_movies),
            'total_genres': len(self.genre_list),
            'rating_distribution': self.ratings_df['rating'].value_counts().sort_index().to_dict(),
            'genres': self.genre_list
        }

    def suggest_movie_names(self, query, limit=10):
        q = query.strip().lower()
        if not q:
            return []
        matches = []
        # Prefix / substring matching
        for title in self.unique_movies:
            if q in title.lower():
                matches.append(title)
                if len(matches) >= limit:
                    break
        return matches

    def get_knowledge_recommendations(self, genre=None, min_viewers=300, min_rating=4.0, limit=10):
        if genre and genre != 'All':
            genre_movies = self.items_df[self.items_df[genre] == 1]['movie title'].unique()
            df = self.movie_stats[self.movie_stats['movie title'].isin(genre_movies)].copy()
        else:
            df = self.movie_stats.copy()

        # 1. Top rated popular movies (with dynamic threshold fallback if needed)
        cur_viewers = min_viewers
        cur_rating = min_rating
        filtered = df[(df['watch_count'] >= cur_viewers) & (df['avg_rating'] >= cur_rating)]
        
        while len(filtered) < limit and cur_viewers > 20:
            cur_viewers = max(20, cur_viewers - 50)
            if cur_rating > 2.5:
                cur_rating -= 0.25
            filtered = df[(df['watch_count'] >= cur_viewers) & (df['avg_rating'] >= cur_rating)]

        top_popular_rated = filtered.sort_values(
            by=['avg_rating', 'watch_count'], ascending=[False, False]
        ).head(limit)

        # 2. Most popular overall
        most_popular = df.sort_values(
            by='watch_count', ascending=False
        ).head(limit)

        # 3. Top average rating (with at least 20 viewers to avoid single 5-star bias)
        top_rated = df[df['watch_count'] >= 20].sort_values(
            by='avg_rating', ascending=False
        ).head(limit)

        def format_rows(rows):
            results = []
            for _, r in rows.iterrows():
                title = r['movie title']
                results.append({
                    'title': title,
                    'avg_rating': round(float(r['avg_rating']), 2),
                    'watch_count': int(r['watch_count']),
                    'genres': self.movie_genres_dict.get(title, [])
                })
            return results

        return {
            'genre': genre or 'All',
            'top_popular_rated': format_rows(top_popular_rated),
            'most_popular': format_rows(most_popular),
            'top_rated': format_rows(top_rated),
            'criteria': {
                'min_viewers_used': cur_viewers,
                'min_rating_used': round(cur_rating, 2)
            }
        }

    def get_knn_movie_recommendations(self, movie_name, top_n=10):
        # Match case-insensitively if needed
        matched_title = None
        if movie_name in self.knn_movie_name_to_idx:
            matched_title = movie_name
        else:
            q_lower = movie_name.lower()
            for title in self.knn_movie_names:
                if title.lower() == q_lower:
                    matched_title = title
                    break

        if not matched_title:
            suggestions = self.suggest_movie_names(movie_name, 5)
            return {'error': 'Movie not found', 'suggestions': suggestions}

        idx = self.knn_movie_name_to_idx[matched_title]
        movie_vector = self.movie_to_user_df.iloc[idx, :].values.reshape(1, -1)
        distances, indices = self.knn_movie_model.kneighbors(movie_vector, n_neighbors=top_n + 1)

        recommendations = []
        for i in range(1, len(distances[0])):
            rec_idx = indices[0][i]
            rec_title = self.knn_movie_names[rec_idx]
            dist = float(distances[0][i])
            sim_score = max(0.0, 1.0 - dist)
            stats = self.movie_stats[self.movie_stats['movie title'] == rec_title]
            avg_r = float(stats['avg_rating'].iloc[0]) if len(stats) > 0 else 0.0
            cnt = int(stats['watch_count'].iloc[0]) if len(stats) > 0 else 0

            recommendations.append({
                'title': rec_title,
                'similarity': round(sim_score * 100, 1),
                'cosine_distance': round(dist, 4),
                'avg_rating': round(avg_r, 2),
                'watch_count': cnt,
                'genres': self.movie_genres_dict.get(rec_title, [])
            })

        return {
            'query_movie': matched_title,
            'recommendations': recommendations
        }

    def get_knn_user_recommendations(self, user_id, n_similar_users=15, n_movies=10):
        if user_id not in self.user_id_to_idx:
            return {'error': f'User ID {user_id} not found in dataset'}

        idx = self.user_id_to_idx[user_id]
        user_vector = self.user_to_movie_df.iloc[idx, :].values.reshape(1, -1)
        distances, indices = self.knn_user_model.kneighbors(user_vector, n_neighbors=n_similar_users + 1)

        similar_user_indices = indices.flatten()[1:]
        sim_distances = distances.flatten()[1:]
        similar_users = [self.knn_user_ids[i] for i in similar_user_indices]

        # Invert / weight distances
        weights = sim_distances / np.sum(sim_distances)
        mov_rtngs_sim_users = self.user_to_movie_df.iloc[similar_user_indices, :].values
        weight_matrix = weights[:, np.newaxis] + np.zeros(self.user_to_movie_df.shape[1])
        weighted_ratings = weight_matrix * mov_rtngs_sim_users
        aggregated_scores = weighted_ratings.sum(axis=0)

        # Movies already watched by target user
        user_watched = set(self.refined_df[self.refined_df['user id'] == user_id]['movie title'])
        
        # Sort recommendations
        ranked_indices = np.argsort(aggregated_scores)[::-1]
        all_movie_names = self.user_to_movie_df.columns

        recommendations = []
        for i in ranked_indices:
            title = all_movie_names[i]
            score = aggregated_scores[i]
            if score <= 0:
                break
            if title not in user_watched:
                stats = self.movie_stats[self.movie_stats['movie title'] == title]
                avg_r = float(stats['avg_rating'].iloc[0]) if len(stats) > 0 else 0.0
                cnt = int(stats['watch_count'].iloc[0]) if len(stats) > 0 else 0
                recommendations.append({
                    'title': title,
                    'predicted_score': round(float(score), 2),
                    'avg_rating': round(avg_r, 2),
                    'watch_count': cnt,
                    'genres': self.movie_genres_dict.get(title, [])
                })
                if len(recommendations) >= n_movies:
                    break

        # Top watched movies by user for context
        user_history = self.refined_df[self.refined_df['user id'] == user_id].sort_values(
            by='rating', ascending=False
        ).head(10)
        history_formatted = [
            {
                'title': r['movie title'],
                'rating': round(float(r['rating']), 1),
                'genres': self.movie_genres_dict.get(r['movie title'], [])
            }
            for _, r in user_history.iterrows()
        ]

        sim_peers = [
            {'user_id': int(u), 'distance': round(float(d), 4)}
            for u, d in zip(similar_users[:5], sim_distances[:5])
        ]

        return {
            'user_id': user_id,
            'user_history': history_formatted,
            'similar_peers': sim_peers,
            'recommendations': recommendations
        }

    def get_svd_movie_recommendations(self, movie_name, top_n=10):
        matched_title = None
        if movie_name in self.svd_movie_to_idx:
            matched_title = movie_name
        else:
            q_lower = movie_name.lower()
            for title in self.svd_movie_names:
                if title.lower() == q_lower:
                    matched_title = title
                    break

        if not matched_title:
            suggestions = self.suggest_movie_names(movie_name, 5)
            return {'error': 'Movie not found', 'suggestions': suggestions}

        idx = self.svd_movie_to_idx[matched_title]
        movie_vec = self.movie_latent_normed[idx]
        sims = self.movie_latent_normed @ movie_vec
        sorted_indices = np.argsort(-sims)

        recommendations = []
        for i in sorted_indices[1:top_n+1]:
            rec_title = self.svd_movie_names[i]
            sim_score = float(sims[i])
            stats = self.movie_stats[self.movie_stats['movie title'] == rec_title]
            avg_r = float(stats['avg_rating'].iloc[0]) if len(stats) > 0 else 0.0
            cnt = int(stats['watch_count'].iloc[0]) if len(stats) > 0 else 0
            recommendations.append({
                'title': rec_title,
                'similarity': round(sim_score * 100, 1),
                'avg_rating': round(avg_r, 2),
                'watch_count': cnt,
                'genres': self.movie_genres_dict.get(rec_title, [])
            })

        return {
            'query_movie': matched_title,
            'recommendations': recommendations
        }

    def get_dnn_user_recommendations(self, user_id, n_movies=10):
        if user_id not in self.svd_user_to_idx:
            return {'error': f'User ID {user_id} not found in dataset'}

        u_col_idx = self.svd_user_to_idx[user_id]
        predicted_ratings = self.svd_reconstructed[:, u_col_idx]
        user_watched = set(self.refined_df[self.refined_df['user id'] == user_id]['movie title'])

        ranked_indices = np.argsort(-predicted_ratings)
        recommendations = []

        for idx in ranked_indices:
            title = self.svd_movie_names[idx]
            if title not in user_watched:
                pred_r = float(predicted_ratings[idx])
                stats = self.movie_stats[self.movie_stats['movie title'] == title]
                avg_r = float(stats['avg_rating'].iloc[0]) if len(stats) > 0 else 0.0
                cnt = int(stats['watch_count'].iloc[0]) if len(stats) > 0 else 0
                recommendations.append({
                    'title': title,
                    'predicted_rating': round(max(1.0, min(5.0, pred_r)), 2),
                    'avg_rating': round(avg_r, 2),
                    'watch_count': cnt,
                    'genres': self.movie_genres_dict.get(title, [])
                })
                if len(recommendations) >= n_movies:
                    break

        return {
            'user_id': user_id,
            'recommendations': recommendations
        }
