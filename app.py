import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, request, session, redirect, url_for, flash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

cred = credentials.Certificate(
    'flight-booking-bce1d-firebase-adminsdk-2b8am-379d4c3a57.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

@app.route('/')
def index():
    return render_template('index.html')


#USER

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user = auth.create_user(
            email=email,
            password=password
        )
        user_ref = db.collection('users').document(user.uid)
        user_ref.set({
            'name': name,
            'email': email,
            'password': password
        })
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_ref = db.collection('users').where(
            'email', '==', email).limit(1).get()
        if len(user_ref) > 0 and user_ref[0].to_dict()['password'] == password:
            session['email'] = email
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid email or password")
    else:
        return render_template('login.html')
    
@app.route('/dashboard')
@login_required
def dashboard():
    if 'email' in session:
        email = session['email']
        return render_template('dashboard.html', email=email)
    else:
        return redirect(url_for('login'))
    
@app.route('/search_flights', methods=['GET', 'POST'])
def search_flights():
    if request.method == 'POST':
        departure = request.form.get('departure')
        arrival = request.form.get('arrival')
        departure_date = request.form.get('departure_date')
        departure_time = request.form.get('departure_time')
        arrival_date = request.form.get('arrival_date')
        arrival_time = request.form.get('arrival_time')
        if not all([departure, arrival, departure_date, departure_time, arrival_date, arrival_time]):
            flash('Please enter all required fields')
            return redirect(url_for('search_flights'))
        flights = db.collection('flights').where('departure', '==', departure).where('arrival', '==', arrival).where('departure_date', '==', departure_date).where(
            'departure_time', '==', departure_time).where('arrival_date', '==', arrival_date).where('arrival_time', '==', arrival_time).limit(10).stream()
        flight_data = []
        flights = db.collection('flights').where('departure', '==', departure).where('arrival', '==', arrival).where('departure_date', '==', departure_date).where(
            'departure_time', '==', departure_time).where('arrival_date', '==', arrival_date).where('arrival_time', '==', arrival_time).stream()
        for flight in flights:
            flight_dict = flight.to_dict()
            flight_data.append(flight_dict)
        if not flight_data:
            flash('No flights found')
            return redirect(url_for('search_flights'))
        return render_template('dashboard.html', flight_data=flight_data)
    else:
        return render_template('dashboard.html')
    
@app.route('/bookings', methods=['POST'])
def bookings():
    flight_number = request.form['flight_number']
    email = request.form['email']
    print("Flight number:", flight_number)
    print("User email:", email)
    user_doc = db.collection('users').document(email)
    booking_data = {
        'flight_number': flight_number,
    }
    bookings_collection = user_doc.collection('bookings')
    bookings_collection.add(booking_data)
    return redirect(url_for('mybookings'))

@app.route('/mybookings')
@login_required
def mybookings():
    email = session.get('email')
    if not email:
        flash('Please login to view your bookings.')
        return redirect(url_for('login'))
    user_doc = db.collection('users').document(email)
    bookings_collection = user_doc.collection('bookings')
    bookings = bookings_collection.get()
    booking_data = []
    for booking in bookings:
        data = booking.to_dict()
        data['id'] = booking.id
        flight_number = data.get('flight_number')
        flight_ref = db.collection('flights').where(
            'flight_number', '==', flight_number).get()
        if flight_ref:
            flight_data = flight_ref[0].to_dict()
            data.update(flight_data)
        booking_data.append(data)
    return render_template('mybookings.html', bookings=booking_data)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


#ADMIN

def adminlogin_required(f):
    @wraps(f)
    def admindecorated_function(*args, **kwargs):
        if not session.get('email'):
            return render_template('admin.html')
        return f(*args, **kwargs)
    return admindecorated_function

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@admin' and password == 'admin':
            session['email'] = email
            return redirect(url_for('availflights'))
        else:
            return render_template('admin.html', error="Invalid email or password")
    return render_template('admin.html')

@app.route('/availflights')
@adminlogin_required
def availflights():
    flights_ref = db.collection('flights')
    flights = flights_ref.get()
    flights_data = []
    for flight in flights:
        flights_data.append(flight.to_dict())
    bookings_ref = db.collection_group('bookings')
    bookings = bookings_ref.get()
    booking_data = []
    print(f"Number of bookings: {len(bookings)}")
    for booking in bookings:
        data = booking.to_dict()
        data['id'] = booking.id
        flight_number = data.get('flight_number')
        flight_ref = db.collection('flights').where(
            'flight_number', '==', flight_number).get()
        if flight_ref:
            flight_data = flight_ref[0].to_dict()
            data.update(flight_data)
        user_email = booking.reference.parent.parent.id
        print(f"User email: {user_email}")
        if user_email:
            users_ref = db.collection('users').where('email', '==', user_email)
            user_query = users_ref.get()
            if not user_query:
                print(f"No user found with email: {user_email}")
            else:
                user_data = user_query[0]
                user_dict = user_data.to_dict()
                print(f"user_dict: {user_dict}")
                data['name'] = user_dict.get('name')
                data['email'] = user_email
                print(f"name: {data['name']}, email: {data['email']}")
        booking_data.append(data)
    print('Booking data:', booking_data)
    return render_template('admindashboard.html', flights=flights_data, bookings=booking_data)


@app.route('/flights', methods=['POST'])
def create_flight():
    flight_number = request.form.get('flight_number')
    departure = request.form.get('departure')
    arrival = request.form.get('arrival')
    departure_date = request.form.get('departure_date')
    departure_time = request.form.get('departure_time')
    arrival_date = request.form.get('arrival_date')
    arrival_time = request.form.get('arrival_time')
    flight_id = db.collection('flights').document().id
    flight_data = {
        'flight_number': flight_number,
        'departure': departure,
        'arrival': arrival,
        'departure_date': departure_date,
        'departure_time': departure_time,
        'arrival_date': arrival_date,
        'arrival_time': arrival_time
    }
    db.collection('flights').document(flight_id).set(flight_data)
    return redirect(url_for('availflights'))


@app.route('/delflights', methods=['GET', 'POST', 'DELETE'])
def delflights():
    if request.method == 'POST':
        flight_number = request.form['flight_number']
        print(flight_number)
        query = db.collection('flights').where(
            'flight_number', '==', flight_number)
        flights = query.get()
        print(flights)
        for flight in flights:
            flight.reference.delete()
            print(flight.id, 'deleted')
        return redirect(url_for('delflights'))
    return redirect(url_for('availflights'))

@app.route('/adminlogout')
def adminlogout():
    session.pop('email', None)
    flash('You have been logged out', 'success')
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
