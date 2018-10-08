class SqlController:

    def __init__(self):
        self.connection = mysql.connector.connect(
            host = 'localhost',
            port = '3306',
            user = os.environ['CL_SQL_USER'],
            password = os.environ['CL_SQL_PASS'],
            database = os.environ['CL_USE_DB']
        )

    def __del__(self):
        self.connection.close()

    def begin_cursor(self):
        self.cursor = self.connection.cursor(buffered=True)

    def execute(self, query):
        self.cursor.execute(query)

    def commit(self):
        self.connection.commit()

    def quit_cursor(self):
        self.cursor.close()

def insert(db, table, dic):
    db.begin_cursor()
    query  = 'insert into %s ' %(table)
    keys = list(dic.keys())
    values = map(str, list(dic.values()))
    query += '(' + ', '.join(keys) + ') values '
    query += '(' + ', '.join(values) + ')'
    db.execute(query)
    db.commit()
    db.quit_cursor()