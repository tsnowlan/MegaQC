# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify, abort

from megaqc.extensions import db
from megaqc.user.models import User
from megaqc.api.utils import handle_report_data
from megaqc.user.forms import AdminForm

from sqlalchemy.sql import func

from functools import  wraps

api_blueprint = Blueprint('api', __name__, static_folder='../static')


#decorator to handle api authentication
def check_user(function):
    @wraps(function)
    def user_wrap_function(*args, **kwargs):
        user = User.query.filter_by(api_token=request.headers.get("access_token")).first()
        if not user:
            abort(403) #if no user, abort the request with 403 
        kwargs['user'] = user
        return function(*args, **kwargs) #else add "user" to kwargs so it can be used in the request handling
    return user_wrap_function

def check_admin(function):
    @wraps(function)
    def user_wrap_function(*args, **kwargs):
        user = User.query.filter_by(api_token=request.headers.get("access_token")).first()
        if not user or not user.is_admin:
            abort(403) #if no user, abort the request with 403 
        kwargs['user'] = user
        return function(*args, **kwargs) #else add "user" to kwargs so it can be used in the request handling
    return user_wrap_function


@api_blueprint.route('/api/test', methods=['GET'])
@check_user
def test(user, *args, **kwargs):
    return jsonify({'name' : user.username})

@api_blueprint.route('/api/test_post', methods=['POST'])
@check_user
def test_post(user, *args, **kwargs):
    data = request.get_json()
    data['name'] = user.username
    return jsonify(data)


@api_blueprint.route('/api/upload_data', methods=['POST'])
@check_user
def handle_multiqc_data(user, *args, **kwargs):
    data = request.get_json()
    handle_report_data(user, data)
    return jsonify({'ok' : 200})


@api_blueprint.route('/api/update_users', methods=['POST'])
@check_admin
def admin_update_users(user, *args, **kwargs):
    data = request.get_json()
    try:
        user_id = int(data['user_id'])
        data['user_id'] = user_id
    except:
        abort(400)
    cured_data = {key:(data[key] if data[key] != "None" else None) for key in data}
    form = AdminForm(**cured_data)
    if not form.validate():
        response = jsonify({'message': ' '.join(' '.join(errs) for errs in form.errors.values())})
        response.status_code = 400
        return response
    else:
        db.session.query(User).filter(User.user_id==user_id).first().update(**cured_data)
        return jsonify({"ok":200})

@api_blueprint.route('/api/delete_users', methods=['POST'])
@check_admin
def admin_delete_users(user, *args, **kwargs):
    data = request.get_json()
    try:
        user_id = int(data['user_id'])
    except:
        abort(400)
    db.session.query(User).filter(User.user_id==user_id).first().delete()
    return jsonify({"ok":200})

@api_blueprint.route('/api/reset_password', methods=['POST'])
@check_user
def reset_password(user, *args, **kwargs):
    data = request.get_json()
    if user.is_admin or data['user_id'] == user.user_id:
        new_password= user.reset_password()
        user.save()
    else:
        abort(403)
    return jsonify({"ok":200, "password":new_password})

@api_blueprint.route('/api/set_password', methods=['POST'])
@check_user
def set_password(user, *args, **kwargs):
    data = request.get_json()
    user.set_password(data['password'])
    user.save()
    return jsonify({"ok":200})

@api_blueprint.route('/api/add_user', methods=['POST'])
@check_admin
def admin_add_users(user, *args, **kwargs):
    data = request.get_json()
    try:
        data['user_id'] = int(data['user_id'])
    except:
        abort(400)
    new_user= User(**data)
    password = new_user.reset_password()
    new_user.active= True
    new_user.save()
    return jsonify({"ok":200, "password":password, "api_token":user.api_token})

@api_blueprint.route('/api/get_samples_per_report', methods=['POST'])
@check_user
def get_samples_per_report(user, *args, **kwargs):
    data = request.get_json()
    report_ids=data.get("report_id")
    sample_names=db.session.query(PlotData.sample_name).filter(PlotData.report_id ==  report_id).all()
    return jsonify(sample_names)