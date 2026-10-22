import json
import builtins
from datetime import datetime
from app import db


class FoodMenu(db.Model):
    __tablename__ = 'food_menus'

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey('properties.id', ondelete='CASCADE'), unique=True, nullable=False)
    food_type = db.Column(db.String(20), default='both', nullable=False)  # 'veg', 'non_veg', 'both'
    meals_provided = db.Column(db.String(100), default='Breakfast, Dinner (Weekdays), 3 Meals (Weekends)')
    food_included_in_rent = db.Column(db.Boolean, default=True, nullable=False)
    additional_food_charge = db.Column(db.Float, default=0.0)
    breakfast_timings = db.Column(db.String(50), default='7:30 AM - 9:30 AM')
    lunch_timings = db.Column(db.String(50), default='1:00 PM - 2:30 PM')
    dinner_timings = db.Column(db.String(50), default='8:00 PM - 10:00 PM')
    special_sunday_menu = db.Column(db.String(255), default='Chicken Biryani / Veg Biryani with Raitha & Gulab Jamun')
    weekly_menu_data = db.Column(db.Text, nullable=True)  # JSON encoded string of {day: {breakfast, lunch, dinner}}
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    property = db.relationship('Property', back_populates='food_menu')

    @builtins.property
    def menu_dict(self):
        if not self.weekly_menu_data:
            return self.get_default_menu()
        try:
            return json.loads(self.weekly_menu_data)
        except Exception:
            return self.get_default_menu()

    def set_menu_dict(self, menu_dict):
        self.weekly_menu_data = json.dumps(menu_dict)
        self.last_updated_at = datetime.utcnow()

    @staticmethod
    def get_default_menu():
        return {
            'Monday': {
                'breakfast': 'Idli, Vada, Sambar, Coconut Chutney, Tea/Coffee',
                'lunch': 'Rice, Sambar, Rasam, Beans Poriyal, Curd',
                'dinner': 'Roti, Dal Tadka, Aloo Gobi, Rice, Curd'
            },
            'Tuesday': {
                'breakfast': 'Poori, Aloo Masala, Tea/Coffee',
                'lunch': 'Rice, Tomato Dal, Mix Veg Curry, Papad, Buttermilk',
                'dinner': 'Phulka, Paneer Butter Masala, Jeera Rice, Salad'
            },
            'Wednesday': {
                'breakfast': 'Poha / Upma, Mint Chutney, Boiled Egg / Banana, Tea/Coffee',
                'lunch': 'Rice, Sambar, Cabbage Curry, Rasam, Curd',
                'dinner': 'Egg Curry / Mushroom Curry, Chapati, Steamed Rice'
            },
            'Thursday': {
                'breakfast': 'Masala Dosa, Sambar, Chutney, Tea/Coffee',
                'lunch': 'Lemon Rice / Curd Rice, Potato Fry, Papad',
                'dinner': 'Roti, Rajma Masala, Steamed Rice, Gulab Jamun'
            },
            'Friday': {
                'breakfast': 'Aloo Paratha with Curd & Pickle, Tea/Coffee',
                'lunch': 'Rice, Drumstick Sambar, Beetroot Poriyal, Curd',
                'dinner': 'Veg Pulao / Chicken Curry, Phulka, Raitha'
            },
            'Saturday': {
                'breakfast': 'Set Dosa, Vegetable Kurma, Coconut Chutney',
                'lunch': 'South Indian Meals with Sweet Payasam',
                'dinner': 'Roti, Mixed Dal Fry, Bhindi Masala, Rice'
            },
            'Sunday': {
                'breakfast': 'Chole Bhature / Masala Idli, Tea/Coffee',
                'lunch': 'Special Chicken Biryani / Hyderabadi Veg Biryani, Raitha, Salan',
                'dinner': 'Light Dinner: Khichdi, Kadhi, Papad / Dosa'
            }
        }

    def to_dict(self):
        return {
            'id': self.id,
            'food_type': self.food_type,
            'meals_provided': self.meals_provided,
            'food_included_in_rent': self.food_included_in_rent,
            'additional_food_charge': self.additional_food_charge,
            'breakfast_timings': self.breakfast_timings,
            'lunch_timings': self.lunch_timings,
            'dinner_timings': self.dinner_timings,
            'special_sunday_menu': self.special_sunday_menu,
            'weekly_menu': self.menu_dict,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None
        }
