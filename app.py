import os
from flask import Flask, request, jsonify, abort, render_template
from datetime import datetime
from db import db, Product, Order, OrderItem
import traceback
import random
from flask_cors import CORS
import paho.mqtt.client as mqtt

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coffee.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

if not os.path.exists('coffee.db'):
    with app.app_context():
        db.create_all()

mqtt_client = mqtt.Client()
mqtt_client.connect("localhost", 1883, 60)

@app.route('/')
def home():
    return render_template('choice.html')
@app.route('/danhsach')
def staff_get_order():
    return render_template('danhsachorder.html')
@app.route('/get-list-product', methods=['GET'])
def get_list_product():
    try:
        products = Product.query.all()
        product_list = [
            {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "image_path": f"/static/images/{product.image_path}" if not product.image_path.startswith('/static/images/') else product.image_path,
                "notes": product.notes,
            }
            for product in products
        ]
        return jsonify(product_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/create-order', methods=['POST'])
def create_order():
    try:
        data = request.json
        print("Day la data BE nhan duoc",data)
        table_id = data.get('table_id')
        items = data.get('items')  

        if not table_id or not items:
            return jsonify({"error": "Missing required fields"}), 400

        order = Order(table_id=table_id)
        db.session.add(order)
        
        total_price = 0
        for item in items:
            if 'product_id' not in item or 'quantity' not in item:
                return jsonify({"error": "Invalid item data"}), 400

            product = db.session.get(Product, item['product_id'])
            if not product:
                return jsonify({"error": f"Product not found: {item['product_id']}"}), 404

            price = float(product.price) if product.price is not None else 0
            quantity = int(item['quantity']) if item['quantity'] is not None else 0
            # print(item.get('notes'))
            order_item = OrderItem(
                order_id=order.id, 
                product_id=product.id,
                quantity=item['quantity'],
                notes=item.get('notes', '')
            )
            db.session.add(order_item)

            total_price += price * quantity

        order.total_price = total_price
        db.session.commit()
        mqtt_message = f"ban_{table_id}+{total_price}"
        mqtt_client.publish("control", mqtt_message)
        return jsonify({"id": order.id, "total_price": total_price}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error occurred: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/delete-order/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    try:
        success = Order.delete(order_id)
        if success:
            return jsonify({"message": "Order deleted successfully"}), 200
        else:
            return jsonify({"error": "Order not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/check_order', methods=['GET'])
def check_order():
    try:
        order_id = request.args.get('order_id')  
        if not order_id:
            return jsonify({"error": "Order ID is required"}), 400
        order = Order.query.get(order_id)
        
        if not order:
            return jsonify({"error": "Order not found"}), 404

        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        items = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "notes": item.notes,
                "product_name": item.product.name,
                "product_price": item.product.price,
                "total_price": item.product.price * item.quantity
            }
            for item in order_items
        ]
        
        order_details = {
            "id": order.id,
            "table_number": order.table_id,
            "items": items,
            "total_price": order.total_price
        }

        return jsonify(order_details), 200
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")
        return jsonify({"error": "Internal Server Error"}), 500
@app.route('/location', methods=['GET'])
def get_location():
    try:
        state = random.choice(['AgotoC', 'CgotoA'])
        return jsonify({"state": state}), 200
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")  
        return jsonify({"error": "Internal Server Error"}), 500
@app.route('/get_orders', methods=['GET'])
def get_orders():
    try:
        today = datetime.now().date()

        orders = Order.query.filter(
            db.func.date(Order.created_at) == today
        ).order_by(Order.created_at.desc()).all()

        order_list = []
        for order in orders:
            order_items = OrderItem.query.filter_by(order_id=order.id).all()
            items = [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "notes": item.notes,
                    "product_name": item.product.name,
                    "product_price": item.product.price,
                    "total_price": item.product.price * item.quantity,
                }
                for item in order_items
            ]
            order_details = {
                "id": order.id,
                "table_number": order.table_id,
                "items": items,
                "total_price": order.total_price,
                "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            order_list.append(order_details)

        return jsonify(order_list), 200
    except Exception as e:
        app.logger.error(f"Error occurred: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
