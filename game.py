import json
import random
import math
import os
import urllib.request
from typing import Dict, List, Optional
try:
    from shapely.geometry import shape, Point
    from shapely.ops import nearest_points
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Warning: shapely not available, falling back to capital distances")

class GlobleGame:
    """Handles the game logic for the geography guessing game"""
    
    def __init__(self):
        """Initialize a new game"""
        self.countries = self._load_countries()
        self.geojson_data = self._load_geojson()
        self.target_country = random.choice(self.countries)
        self.guesses: List[Dict] = []
        self.players: List[str] = []
        self.guess_count = 0
        
    def _load_countries(self) -> List[Dict]:
        """Load countries data from local GeoJSON file, excluding Israel"""
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        countries_file = os.path.join(script_dir, 'countries.json')
        
        with open(countries_file, 'r') as f:
            geojson_data = json.load(f)
        
        # Extract country data from GeoJSON features, excluding Israel
        countries = []
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            name = props.get('name', '')
            if name and name.lower() != 'israel':
                # Calculate centroid from geometry for hints
                geometry = feature.get('geometry', {})
                centroid = self._calculate_centroid(geometry)
                
                countries.append({
                    'name': name,
                    'lat': centroid[1] if centroid else 0,
                    'lon': centroid[0] if centroid else 0
                })
        
        return countries
    
    def _load_geojson(self) -> Dict:
        """Load GeoJSON data from local file for border calculations"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            countries_file = os.path.join(script_dir, 'countries.json')
            
            with open(countries_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Warning: Could not load GeoJSON data: {e}")
            return {'type': 'FeatureCollection', 'features': []}
    
    def _calculate_centroid(self, geometry: Dict) -> Optional[tuple]:
        """Calculate centroid of a geometry (works for Polygon and MultiPolygon)"""
        if not geometry:
            return None
        
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates', [])
        
        if not coords:
            return None
        
        # For Polygon: coords[0] is the outer ring
        # For MultiPolygon: coords is list of polygons
        try:
            all_points = []
            
            if geom_type == 'Polygon':
                all_points = coords[0]  # Outer ring
            elif geom_type == 'MultiPolygon':
                # Get first polygon's outer ring
                all_points = coords[0][0]
            
            if all_points:
                avg_lon = sum(p[0] for p in all_points) / len(all_points)
                avg_lat = sum(p[1] for p in all_points) / len(all_points)
                return (avg_lon, avg_lat)
        except (IndexError, TypeError):
            pass
        
        return None
    
    def _find_country_geometry(self, country_name: str):
        """Find country geometry from GeoJSON"""
        if not SHAPELY_AVAILABLE or not self.geojson_data:
            return None
        
        country_lower = country_name.lower()
        
        # Name variations to match GeoJSON
        name_map = {
            'united states': 'united states of america',
            'usa': 'united states of america',
            'uk': 'united kingdom',
            'dr congo': 'democratic republic of the congo',
            'congo': 'republic of the congo',
            'ivory coast': "côte d'ivoire",
            'czech republic': 'czech republic',
            'south korea': 'republic of korea',
            'north korea': "democratic people's republic of korea",
        }
        
        search_name = name_map.get(country_lower, country_lower)
        
        for feature in self.geojson_data.get('features', []):
            feature_name = feature['properties'].get('name', '').lower()
            if feature_name == search_name or feature_name == country_lower:
                try:
                    return shape(feature['geometry'])
                except Exception as e:
                    print(f"Error creating shape for {country_name}: {e}")
                    return None
        
        return None

    def _normalize_country_name(self, name: str) -> str:
        """Normalize country name and map common aliases to canonical names."""
        if not name:
            return ''
        n = name.lower().strip()
        # Remove common punctuation
        n = n.replace('.', '').replace("'", '')

        alias_map = {
            'united states': 'united states of america',
            'usa': 'united states of america',
            'us': 'united states of america',
            'america': 'united states of america',
            'u s': 'united states of america',
            'u s a': 'united states of america',
            'uk': 'united kingdom',
            'great britain': 'united kingdom',
            'britain': 'united kingdom',
            'dr congo': 'democratic republic of the congo',
            'drc': 'democratic republic of the congo',
            'congo-kinshasa': 'democratic republic of the congo',
            'congo': 'republic of the congo',
            'ivory coast': "côte d'ivoire",
            'cote divoire': "côte d'ivoire",
            'czechia': 'czech republic',
            'south korea': 'republic of korea',
            'north korea': "democratic people's republic of korea",
            'russia': 'russian federation',
        }

        return alias_map.get(n, n)
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth
        Uses the Haversine formula
        Returns distance in kilometers
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        
        return c * r
    
    def _find_country(self, country_name: str) -> Optional[Dict]:
        """Find a country by name (case-insensitive)"""
        country_name_norm = self._normalize_country_name(country_name)

        for country in self.countries:
            stored_norm = self._normalize_country_name(country.get('name', ''))
            if stored_norm == country_name_norm:
                return country

        return None
    
    def _already_guessed(self, country_name: str) -> bool:
        """Check if a country has already been guessed"""
        country_norm = self._normalize_country_name(country_name)
        return any(self._normalize_country_name(guess['country']['name']) == country_norm for guess in self.guesses)
    
    def _calculate_distance(self, guessed_country: Dict) -> float:
        """Calculate distance between guessed country and target using borders"""
        if SHAPELY_AVAILABLE:
            try:
                # Get geometries for both countries
                guess_geom = self._find_country_geometry(guessed_country['name'])
                target_geom = self._find_country_geometry(self.target_country['name'])
                
                if guess_geom and target_geom:
                    # Calculate minimum distance between borders
                    distance_degrees = guess_geom.distance(target_geom)
                    
                    # Convert degrees to kilometers (approximate)
                    # 1 degree ≈ 111 km at the equator
                    distance_km = distance_degrees * 111
                    
                    # If countries share a border (distance = 0), return a small value
                    if distance_km < 0.1:
                        return 0.0
                    
                    return distance_km
                
                # Fallback to centroid distance if geometries found
                if guess_geom and target_geom:
                    guess_centroid = guess_geom.centroid
                    target_centroid = target_geom.centroid
                    return self._haversine_distance(
                        guess_centroid.y, guess_centroid.x,
                        target_centroid.y, target_centroid.x
                    )
            except Exception as e:
                print(f"Error calculating border distance: {e}")
        
        # If shapely not available or error occurred, return a large distance
        print(f"Warning: Could not calculate distance between {guessed_country['name']} and {self.target_country['name']}")
        return 10000.0  # Return a large distance as fallback
    
    def _get_feedback(self, distance_km: float) -> str:
        """Get temperature feedback based on distance"""
        if distance_km < 500:
            return "🔥🔥🔥 BURNING HOT!"
        elif distance_km < 1000:
            return "🔥🔥 Very Hot"
        elif distance_km < 2500:
            return "🔥 Hot"
        elif distance_km < 5000:
            return "🌡️ Warm"
        elif distance_km < 7500:
            return "❄️ Cool"
        elif distance_km < 10000:
            return "❄️❄️ Cold"
        else:
            return "❄️❄️❄️ FREEZING!"
    
    def _get_trend(self, current_distance: float) -> str:
        """Determine if getting hotter or colder compared to last guess"""
        if not self.guesses:
            return "first"
        
        last_distance = self.guesses[-1]['distance']
        
        # Threshold for "about the same"
        threshold = 100  # km
        
        if abs(current_distance - last_distance) < threshold:
            return "same"
        elif current_distance < last_distance:
            return "hotter"
        else:
            return "colder"
    
    def make_guess(self, country_name: str, player_name: str) -> Dict:
        """
        Process a guess
        Returns a dictionary with the result status and relevant information
        """
        # Check if country exists
        guessed_country = self._find_country(country_name)
        if not guessed_country:
            return {
                'status': 'invalid',
                'country': country_name
            }
        
        # Check if already guessed
        if self._already_guessed(country_name):
            return {
                'status': 'duplicate',
                'country': guessed_country['name']
            }
        
        # Track player
        if player_name not in self.players:
            self.players.append(player_name)
        
        # Calculate distance
        distance = self._calculate_distance(guessed_country)
        
        # Get trend
        trend = self._get_trend(distance)
        
        # Store guess
        self.guess_count += 1
        self.guesses.append({
            'country': guessed_country,
            'distance': distance,
            'player': player_name,
            'number': self.guess_count
        })
        
        # Check if won
        if guessed_country['name'] == self.target_country['name']:
            return {
                'status': 'won',
                'country': guessed_country['name'],
                'guess_count': self.guess_count,
                'players': self.players
            }
        
        # Return feedback
        return {
            'status': 'guess',
            'country': guessed_country['name'],
            'distance': distance,
            'feedback': self._get_feedback(distance),
            'trend': trend,
            'guess_count': self.guess_count
        }
    
    def get_hint(self) -> str:
        """Get a hint about the target country"""
        hints = []
        
        # First letter of country name
        name = self.target_country['name']
        hints.append(f"📝 First letter: {name[0]}")
        
        # Number of letters
        hints.append(f"🔢 Number of letters: {len(name)}")
        
        # Closest guess hint
        if self.guesses:
            closest = min(self.guesses, key=lambda x: x['distance'])
            hints.append(f"🎯 Closest guess so far: {closest['country']['name']} ({closest['distance']:.0f} km away)")
        
        # Hemisphere hints
        lat = self.target_country.get('lat', 0)
        lon = self.target_country.get('lon', 0)
        
        ns_hemisphere = "Northern" if lat >= 0 else "Southern"
        ew_hemisphere = "Eastern" if lon >= 0 else "Western"
        hints.append(f"🌍 Hemispheres: {ns_hemisphere} & {ew_hemisphere}")
        
        return "\n".join(hints)
    
    def get_stats(self) -> Dict:
        """Get current game statistics"""
        closest_guess = None
        closest_distance = float('inf')
        
        if self.guesses:
            closest = min(self.guesses, key=lambda x: x['distance'])
            closest_guess = closest['country']['name']
            closest_distance = closest['distance']
        
        return {
            'guess_count': self.guess_count,
            'players': self.players,
            'closest_guess': closest_guess,
            'closest_distance': closest_distance
        }
    
    def get_guesses_for_map(self) -> List[Dict]:
        """Get all guesses formatted for map visualization"""
        return self.guesses
