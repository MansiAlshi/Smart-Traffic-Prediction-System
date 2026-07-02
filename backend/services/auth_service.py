from werkzeug.security import generate_password_hash, check_password_hash
from backend.extensions import mysql


def register_user(username, email, password, full_name='', city='Mumbai', phone_number=''):
    cur = mysql.connection.cursor()
    cur.execute('SELECT user_id FROM Users WHERE username = %s OR email = %s', (username, email))
    if cur.fetchone():
        cur.close()
        return None, 'Username or email already exists'

    pw_hash = generate_password_hash(password)
    cur.execute(
        'INSERT INTO Users (username, email, password_hash, full_name, city, phone_number) VALUES (%s, %s, %s, %s, %s, %s)',
        (username, email, pw_hash, full_name, city, phone_number or None)
    )
    mysql.connection.commit()
    user_id = cur.lastrowid
    cur.close()
    return user_id, None


def authenticate_user(username, password):
    cur = mysql.connection.cursor()
    cur.execute(
        'SELECT user_id, username, email, password_hash, full_name, city FROM Users WHERE username = %s AND is_active = 1',
        (username,)
    )
    user = cur.fetchone()
    if not user:
        cur.close()
        return None, 'Invalid username or password'

    if not check_password_hash(user['password_hash'], password):
        cur.close()
        return None, 'Invalid username or password'

    cur.execute('UPDATE Users SET last_login = NOW() WHERE user_id = %s', (user['user_id'],))
    mysql.connection.commit()
    cur.close()
    return user, None


def get_user_profile(user_id):
    cur = mysql.connection.cursor()
    cur.execute(
        '''SELECT user_id, username, email, full_name, city, phone_number,
                  route_preference, created_at, last_login
           FROM Users WHERE user_id = %s''',
        (user_id,)
    )
    user = cur.fetchone()
    cur.close()
    return user


def update_user_profile(user_id, full_name, city, email, phone_number='', route_preference='fastest'):
    cur = mysql.connection.cursor()
    cur.execute(
        '''UPDATE Users SET full_name = %s, city = %s, email = %s,
           phone_number = %s, route_preference = %s WHERE user_id = %s''',
        (full_name, city, email, phone_number, route_preference, user_id)
    )
    mysql.connection.commit()
    cur.close()


def change_user_password(user_id, current_password, new_password):
    cur = mysql.connection.cursor()
    cur.execute('SELECT password_hash FROM Users WHERE user_id = %s', (user_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return False, 'User not found'
    if not check_password_hash(row['password_hash'], current_password):
        cur.close()
        return False, 'Current password is incorrect'
    new_hash = generate_password_hash(new_password)
    cur.execute('UPDATE Users SET password_hash = %s WHERE user_id = %s', (new_hash, user_id))
    mysql.connection.commit()
    cur.close()
    return True, 'Password updated successfully'


def delete_user(user_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute('DELETE FROM Users WHERE user_id = %s', (user_id,))
        mysql.connection.commit()
        cur.close()
        return True, 'Account deleted successfully'
    except Exception as e:
        return False, str(e)


def check_email_exists(email):
    cur = mysql.connection.cursor()
    cur.execute('SELECT user_id FROM Users WHERE email = %s', (email,))
    row = cur.fetchone()
    cur.close()
    return row is not None
