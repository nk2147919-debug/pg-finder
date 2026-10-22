from sqlalchemy import or_, and_, func
from app.models.property import Property, Amenity, PropertyAmenity
from app.models.room import RoomType
from app.models.food import FoodMenu
from app.models.interaction import Review
from app.models.gym import GymFacility


def search_properties(filters, page=1, per_page=9):
    """
    Search and filter properties based on user criteria.
    Only approved listings are visible to customers.
    """
    query = Property.query.filter(Property.status == 'approved')

    # Locality search / general keyword
    q = filters.get('q', '').strip()
    locality = filters.get('locality', '').strip()

    if locality and locality != 'all':
        query = query.filter(Property.locality.ilike(f'%{locality}%'))
    elif q:
        query = query.filter(
            or_(
                Property.locality.ilike(f'%{q}%'),
                Property.name.ilike(f'%{q}%'),
                Property.address.ilike(f'%{q}%'),
                Property.nearest_landmark.ilike(f'%{q}%'),
                Property.sub_locality.ilike(f'%{q}%')
            )
        )

    # Gender Policy
    gender = filters.get('gender')
    if gender and gender in ['gents', 'ladies', 'unisex']:
        query = query.filter(Property.gender_policy == gender)

    # Available beds requirement
    only_available = filters.get('only_available')
    if only_available in ['true', '1', True]:
        query = query.join(RoomType).filter(RoomType.vacant_beds > 0).distinct()

    # Budget Filter (Min & Max Rent)
    min_rent = filters.get('min_rent')
    max_rent = filters.get('max_rent')
    if min_rent or max_rent:
        query = query.join(RoomType)
        if min_rent:
            try:
                query = query.filter(RoomType.monthly_rent >= float(min_rent))
            except ValueError:
                pass
        if max_rent:
            try:
                query = query.filter(RoomType.monthly_rent <= float(max_rent))
            except ValueError:
                pass
        query = query.distinct()

    # Room Sharing Options
    sharing = filters.getlist('sharing') if hasattr(filters, 'getlist') else filters.get('sharing', [])
    if isinstance(sharing, str):
        sharing = [sharing] if sharing else []
    if sharing:
        query = query.join(Property.room_types).filter(RoomType.sharing_type.in_(sharing)).distinct()

    # Room Features: AC, Attached Bathroom
    if filters.get('ac') in ['true', '1', True]:
        query = query.join(Property.room_types).filter(RoomType.has_ac == True).distinct()

    if filters.get('attached_bath') in ['true', '1', True]:
        query = query.join(Property.room_types).filter(RoomType.has_attached_bathroom == True).distinct()

    # Food Filter
    food_type = filters.get('food_type')
    food_included = filters.get('food_included')
    if food_type or food_included in ['true', '1', True]:
        query = query.outerjoin(FoodMenu)
        if food_type in ['veg', 'non_veg', 'both']:
            query = query.filter(FoodMenu.food_type == food_type)
        if food_included in ['true', '1', True]:
            query = query.filter(FoodMenu.food_included_in_rent == True)

    # Amenities Filter (e.g. Wi-Fi, Power Backup, Laundry, CCTV, etc.)
    amenities = filters.getlist('amenities') if hasattr(filters, 'getlist') else filters.get('amenities', [])
    if isinstance(amenities, str):
        amenities = [amenities] if amenities else []
    if amenities:
        for amen_slug in amenities:
            query = query.filter(
                Property.amenities.any(
                    PropertyAmenity.amenity.has(Amenity.slug == amen_slug)
                )
            )

    # In-House Gym Filter
    has_gym = filters.get('has_gym')
    if has_gym in ['true', '1', True]:
        query = query.filter(
            Property.gym_facility.has(
                and_(
                    GymFacility.is_available == True,
                    GymFacility.is_temporarily_unavailable == False
                )
            )
        )

    # Sorting
    sort_by = filters.get('sort_by', 'freshness')
    if sort_by == 'price_asc':
        # Subquery for min rent or sort in memory if needed; standard order by availability or price
        query = query.order_by(Property.availability_last_confirmed_at.desc())
    elif sort_by == 'price_desc':
        query = query.order_by(Property.availability_last_confirmed_at.desc())
    elif sort_by == 'recent':
        query = query.order_by(Property.created_at.desc())
    else:  # default 'freshness'
        query = query.order_by(Property.availability_last_confirmed_at.desc(), Property.is_featured.desc())

    # Execute query
    all_properties = query.all()

    # In-memory post-sort for accurate min starting price
    if sort_by == 'price_asc':
        all_properties.sort(key=lambda p: p.starting_price)
    elif sort_by == 'price_desc':
        all_properties.sort(key=lambda p: p.starting_price, reverse=True)
    elif sort_by == 'rating':
        all_properties.sort(key=lambda p: p.average_rating or 0, reverse=True)

    total_count = len(all_properties)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = all_properties[start:end]
    total_pages = (total_count + per_page - 1) // per_page if per_page else 1

    return {
        'items': paginated_items,
        'total': total_count,
        'page': page,
        'pages': max(1, total_pages),
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1,
        'next_num': page + 1
    }
