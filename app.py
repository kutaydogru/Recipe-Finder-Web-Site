from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "gizli_anahtar"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# API Configuration
API_KEY = '154865bb1aac486cace70d464b6449b7'
BASE_URL = 'https://api.spoonacular.com/recipes/'

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Comment Model
class Comment(db.Model):
    comment_id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))

with app.app_context():
    db.create_all()

# Şifreyi hashleme fonksiyonu
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':  # Kullanıcı giriş yapmayı denerse
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)

        # Veritabanında kullanıcıyı ara
        user = User.query.filter_by(username=username, password=hashed_password).first()

        if user:  # Kullanıcı bulunduysa
            session['user_id'] = user.id
            return redirect(url_for('search_recipes'))  # Başarılı girişte yönlendir

        # Kullanıcı bulunmazsa hata mesajı
        flash('Invalid username or password.', 'danger')

    # GET isteğinde sadece login sayfasını döndür
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':  # Kullanıcı kayıt olmaya çalışıyorsa
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)  # Şifreyi hashle

        # Kullanıcı adının mevcut olup olmadığını kontrol et
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:  # Kullanıcı adı zaten varsa
            flash('Username already exists. Please try another username.', 'danger')
            return redirect(url_for('signup'))

        # Yeni kullanıcı oluştur ve kaydet
        try:
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))  # Kayıt sonrası giriş sayfasına yönlendirme
        except Exception as e:  # Diğer veritabanı hatalarını yakala
            flash('An error occurred while creating your account. Please try again.', 'danger')
            print(f"Error: {e}")  # Opsiyonel loglama

    # GET isteğinde sadece kayıt formunu döndür
    return render_template('signup.html')

@app.route('/search', methods=['GET', 'POST'])
def search_recipes():
    if 'user_id' not in session:
        flash('Please log in to search for recipes.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        ingredients = request.form.get('ingredients')

        try:
            response = requests.get(f'{BASE_URL}findByIngredients', params={
                'ingredients': ingredients,
                'number': 10,
                'ranking': 2,
                'ignorePantry': True,
                'apiKey': API_KEY
            })
            response.raise_for_status()

            if response.status_code != 200:
                flash("Failed to fetch recipes. Please try again.", "danger")
                return redirect(url_for('search_recipes'))

            recipes = response.json()
            if not recipes:
                flash("Enter the materials in the desired format. Don't forget to put a comma between the materials.", "warning")
                return redirect(url_for('search_recipes'))

            filtered_recipes = [recipe for recipe in recipes if recipe.get('usedIngredients')]
            return render_template('recipes.html', recipes=filtered_recipes)

        except requests.exceptions.RequestException as e:
            flash("Failed to fetch recipes. Please check your connection or try again.", "danger")
            print(f"API Error: {e}")  # Opsiyonel loglama
            return redirect(url_for('search_recipes'))

    return render_template('search.html')

@app.route('/recipe/<int:id>', methods=['GET', 'POST'])
def recipe_details(id):
    response_details = requests.get(f'{BASE_URL}{id}/information', params={'apiKey': API_KEY})
    response_instructions = requests.get(f'{BASE_URL}{id}/analyzedInstructions', params={'stepBreakdown': True, 'apiKey': API_KEY})

    recipe_details = response_details.json()
    recipe_steps = response_instructions.json()

    # Fetch comments for the recipe
    comments = Comment.query.filter_by(recipe_id=id).all()

    # Eğer talimatlar yoksa uyarı göster
    if not recipe_steps or len(recipe_steps) == 0 or 'steps' not in recipe_steps[0]:
        return "No instructions available for this recipe.", 404

    # Malzeme resimlerini tam URL'ye dönüştür
    ingredients = recipe_details.get('extendedIngredients', [])
    for ingredient in ingredients:
        if 'image' in ingredient:
            ingredient['image'] = f"https://spoonacular.com/cdn/ingredients_100x100/{ingredient['image']}"

    # Tarif detaylarını şablona gönder
    return render_template(
        'recipe_details.html',
        title=recipe_details.get('title', 'Recipe Details'),
        image=recipe_details.get('image'),
        ingredients=ingredients,
        steps=recipe_steps,
        comments=comments,
        id=id  # Pass the id to the template
    )

@app.route('/add_comment/<int:recipe_id>', methods=['POST'])
def add_comment(recipe_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_id = session['user_id']
        comment_text = request.form.get('comment_text')

        if not comment_text:
            flash("Comment cannot be empty.", "warning")
            return redirect(url_for('recipe_details', id=recipe_id))

        new_comment = Comment(recipe_id=recipe_id, user_id=user_id, comment_text=comment_text)
        db.session.add(new_comment)
        db.session.commit()

        return redirect(url_for('recipe_details', id=recipe_id))
    
    except Exception as e:
        flash("An error occurred while adding your comment. Please try again.", "danger")
        print(f"Error: {e}")  # Opsiyonel loglama
        return redirect(url_for('recipe_details', id=recipe_id))

@app.route('/recipe_book')
def recipe_book():
    if 'user_id' not in session:
        flash("You need to log in to view your Recipe Book.", "warning")
        return redirect(url_for('login'))

    user_id = session['user_id']
    recipes = RecipeBook.query.filter_by(user_id=user_id).all()
    return render_template('recipe_book.html', recipes=recipes)

if __name__ == '__main__':
    app.run(debug=True)