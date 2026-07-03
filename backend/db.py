import pymysql
from flask import g, current_app


def get_db():
    if 'db' not in g:
        # Aiven and most hosted MySQL providers require SSL
        use_ssl = current_app.config.get('MYSQL_SSL', False)
        ssl_params = {'ssl': {}} if use_ssl else {}
        g.db = pymysql.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            port=current_app.config['MYSQL_PORT'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            **ssl_params,
        )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


class MySQL:
    @property
    def connection(self):
        return get_db()

    def init_app(self, app):
        app.teardown_appcontext(close_db)


db = MySQL()
