from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def __init__(self, name, price, image_path=None, notes=None):
        self.name = name
        self.price = price
        self.image_path = image_path
        self.notes = notes

    @staticmethod
    def create(name, price, image_path=None, notes=None):
        product = Product(name=name, price=price, image_path=image_path, notes=notes)
        db.session.add(product)
        db.session.commit()
        return product

    @staticmethod
    def read(product_id):
        return Product.query.get(product_id)

    @staticmethod
    def update(product_id, name=None, price=None, image_path=None, notes=None):
        product = Product.query.get(product_id)
        if product:
            if name: product.name = name
            if price: product.price = price
            if image_path: product.image_path = image_path
            if notes: product.notes = notes
            db.session.commit()
        return product

    @staticmethod
    def delete(product_id):
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            return True
        return False


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create(table_id):
        order = Order(table_id=table_id)
        db.session.add(order)
        db.session.commit()
        return order

    @staticmethod
    def read(order_id):
        return Order.query.get(order_id)

    @staticmethod
    def update(order_id, table_id=None):
        order = Order.query.get(order_id)
        if order:
            if table_id: order.table_id = table_id
            db.session.commit()
        return order

    @staticmethod
    def delete(order_id):
        order = Order.query.get(order_id)
        if order:
            db.session.delete(order)
            db.session.commit()
            return True
        return False


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    @staticmethod
    def create(order_id, product_id, quantity, notes=None):
        order_item = OrderItem(
            order_id=order_id, 
            product_id=product_id,
            quantity=quantity,
            notes=notes
        )
        db.session.add(order_item)

        order = Order.query.get(order_id)
        product = Product.query.get(product_id)
        if order and product:
            order.total_price += product.price * quantity
        
        db.session.commit()
        return order_item

    @staticmethod
    def read(order_item_id):
        return OrderItem.query.get(order_item_id)

    @staticmethod
    def update(order_item_id, quantity=None, notes=None):
        order_item = OrderItem.query.get(order_item_id)
        if order_item:
            if quantity:
                order = order_item.order
                product = order_item.product
                order.total_price -= product.price * order_item.quantity
                order.total_price += product.price * quantity
                order_item.quantity = quantity
            
            if notes:
                order_item.notes = notes
            
            db.session.commit()
        return order_item

    @staticmethod
    def delete(order_item_id):
        order_item = OrderItem.query.get(order_item_id)
        if order_item:
            order = order_item.order
            product = order_item.product
            order.total_price -= product.price * order_item.quantity
            
            db.session.delete(order_item)
            db.session.commit()
            return True
        return False