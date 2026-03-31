# components/map.py
"""
Composant de la carte
"""
import geemap.foliumap as geemap
from utils.geometry import add_polygon_to_map


def create_map(st_session_state, lat, lon):
    """Crée et configure la carte"""
    
    if st_session_state.get('polygon_bounds'):
        center_lat, center_lon, zoom = st_session_state.polygon_bounds
        m = geemap.Map(center=[center_lat, center_lon], zoom=zoom)
    else:
        m = geemap.Map(center=[lat, lon], zoom=7)
    
    m.add_basemap('SATELLITE')
    
    try:
        m.add_draw_control(
            draw_options={
                'polygon': True,
                'rectangle': True,
                'circle': True,
                'marker': False,
                'circlemarker': False
            },
            edit_options={
                'edit': True,
                'remove': True
            }
        )
    except:
        try:
            m.add_draw_control()
        except:
            pass
    
    if st_session_state.get('polygon_coords'):
        st_session_state.ee_polygon = add_polygon_to_map(m, st_session_state.polygon_coords, color='red', weight=3)
    
    return m