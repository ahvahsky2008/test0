from flask.globals import request
from flask.templating import render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists, create_database
from flask import Flask, session, flash, redirect, url_for, abort, jsonify
from webargs.flaskparser import use_kwargs
from webargs import fields
from typing import Iterable, Iterator
import sys
from faker import Faker

FIELD_NAMES = ['email', 'phone', 'message']
app = Flask(__name__)

def must_match_field_name(value):
    return value in FIELD_NAMES

app.secret_key = "3dd2feafa14a4ff7a04e2c2157c6ecfc"

#Хак для того чтобы можно было в режиме отладки или запуска из venv цепляться к sqlite-базе. В проде из докера будет цепляться к postgresql
if len(sys.argv)==2 or __debug__:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hello_flask:hello_flask@db:5432/hello_flask_dev'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(255), nullable=False, server_default='')
    message = db.Column(db.String(255), nullable=True, server_default='')

    def to_dict(self):
        return dict([(k, getattr(self, k)) for k in self.__dict__.keys() if not k.startswith("_")])

    @classmethod
    def seed(cls, fake):
        message = Message(
            phone = fake.phone_number(),
            email = fake.email(),
            message = fake.paragraph(nb_sentences=1)
        )
        message.save()
    
    def save(self):
        db.session.add(self)
        db.session.commit()
        
db.create_all()

def prepare_data(data: Iterable[dict]) -> Iterator[dict]:
    for datum in data:
        yield datum

def filtered_results(data: Iterable[dict],
                     query: str,
                     field: str) -> Iterator[dict]:
    if not query:
        yield from data
        return

    for datum in data:
        if field:
            if query.lower() in datum[field].lower():
                yield datum
        else:
            for field_name in FIELD_NAMES:
                if query.lower() in datum[field_name].lower():
                    yield datum
                    break


@app.route("/seed", methods=['GET', 'POST'])
def seed():
    fake = Faker()
    for _ in range(100):
        Message.seed(fake)
    return redirect(url_for('search'))


@app.route("/add", methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        try:
            email = request.json['email']
            phone = request.json['phone']
            message = request.json['message']
            message = Message(email=email, phone=phone, message=message)
            db.session.add(message)
            db.session.commit()
            return 'ok'

        except Exception as e:
            return 'error'

@app.route("/search", methods=['get'])
@use_kwargs({
    'query': fields.Str(missing=None),
    'field': fields.Str(missing=None, validate=must_match_field_name),
    'size': fields.Int(missing=20),
    'offset': fields.Int(missing=0)
})
def search_api(query, field, size, offset):

    data = Message.query.all()
    
    pure_data = []
    for d in data:
        pure_data.append(d.to_dict())

    prepped_data = prepare_data(pure_data)
    results = list(filtered_results(prepped_data, query, field))

    index_start = size * offset
    if index_start > len(results):
        abort(400)
    index_stop = min(size + (size * offset), len(results))

    body = {
        'results': results[index_start:index_stop],
        'total': len(results)
    }
    return jsonify(body)

@app.route("/", methods=['get'])
def search():
    return render_template('search.html')

@app.route("/create")
def create():
    return render_template('create.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5555)