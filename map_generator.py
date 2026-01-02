import json
import os
import tempfile
import time
from typing import List, Dict, Optional

import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.geometry import shape


class MapGenerator:
    """Generate realistic maps with entire countries colored using OpenStreetMap tiles."""

    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        countries_file = os.path.join(script_dir, 'countries.json')

        with open(countries_file, 'r', encoding='utf-8') as f:
            self.geojson_data = json.load(f)

        # Filter out Israel if present (user requested removal)
        self.geojson_data['features'] = [
            feat for feat in self.geojson_data.get('features', [])
            if feat.get('properties', {}).get('name', '').strip().lower() != 'israel'
        ]

    def _find_feature_by_name(self, country_name: str) -> Optional[Dict]:
        for feature in self.geojson_data.get('features', []):
            if self._match_country_name(feature.get('properties', {}).get('name', ''), country_name):
                return feature
        return None

    def _get_color_from_distance(self, distance_km: float) -> str:
        if distance_km < 500:
            return '#FF0000'
        elif distance_km < 1000:
            return '#FF4500'
        elif distance_km < 2500:
            return '#FF8C00'
        elif distance_km < 5000:
            return '#FFD700'
        elif distance_km < 7500:
            return '#87CEEB'
        elif distance_km < 10000:
            return '#4169E1'
        else:
            return '#00008B'

    def _get_temperature_label(self, distance_km: float) -> str:
        if distance_km < 500:
            return '🔥🔥🔥 BURNING HOT'
        elif distance_km < 1000:
            return '🔥🔥 Very Hot'
        elif distance_km < 2500:
            return '🔥 Hot'
        elif distance_km < 5000:
            return '🌡️ Warm'
        elif distance_km < 7500:
            return '❄️ Cool'
        elif distance_km < 10000:
            return '❄️❄️ Cold'
        else:
            return '❄️❄️❄️ FREEZING'

    def _match_country_name(self, geojson_name: str, guess_name: str) -> bool:
        geo_lower = (geojson_name or '').lower().strip()
        guess_lower = (guess_name or '').lower().strip()
        if not geo_lower or not guess_lower:
            return False
        if geo_lower == guess_lower:
            return True

        variations = {
            'united states of america': ['united states', 'usa', 'us'],
            'united kingdom': ['uk', 'great britain', 'britain'],
            'democratic republic of the congo': ['dr congo', 'drc', 'congo-kinshasa'],
            'republic of the congo': ['congo', 'congo-brazzaville'],
            'south korea': ['korea, republic of'],
            'north korea': ["korea, democratic people's republic of"],
            'tanzania': ['tanzania, united republic of'],
            'russia': ['russian federation'],
            "cote d'ivoire": ["ivory coast"],
            'czech republic': ['czechia'],
        }

        for standard, alts in variations.items():
            if geo_lower == standard and guess_lower in alts:
                return True
            if guess_lower == standard and geo_lower in alts:
                return True
        return False

    def generate_guess_map(self, guesses: List[Dict], target_country: Dict, guess_count: int) -> str:
        """Render a PNG map showing guessed countries highlighted.

        Returns path to a temporary PNG file.
        """
        features = self.geojson_data.get('features', [])
        if not features:
            raise RuntimeError('No GeoJSON features available')

        gdf = gpd.GeoDataFrame.from_features(features)
        # Ensure geometries are correct
        if gdf.geometry.isnull().any():
            gdf['geometry'] = gdf['geometry'].apply(lambda g: shape(g) if isinstance(g, dict) else g)

        # Set CRS to web mercator for contextily
        gdf = gdf.set_crs(epsg=4326, allow_override=True).to_crs(epsg=3857)

        # Build guess lookup
        guess_info = {}
        for guess_data in guesses:
            country_name = guess_data['country']['name']
            distance = guess_data.get('distance', 0)
            guess_info[country_name.lower()] = {
                'color': self._get_color_from_distance(distance),
                'distance': distance,
                'label': self._get_temperature_label(distance),
                'country': country_name,
            }

        # Default styles
        gdf['style_color'] = '#E8E8E8'
        gdf['alpha'] = 0.4
        gdf['edgecolor'] = '#999999'
        gdf['linewidth'] = 0.5

        # Apply guessed styles
        for idx, row in gdf.iterrows():
            name = row.get('properties', {}).get('name') if isinstance(row.get('properties'), dict) else row.get('name', '')
            for guess_name, info in guess_info.items():
                if self._match_country_name(name or row.get('name', ''), guess_name):
                    gdf.at[idx, 'style_color'] = info['color']
                    gdf.at[idx, 'alpha'] = 0.75
                    gdf.at[idx, 'edgecolor'] = 'white'
                    gdf.at[idx, 'linewidth'] = 1.5
                    break

        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        gdf.plot(ax=ax, color=gdf['style_color'], linewidth=gdf['linewidth'], edgecolor=gdf['edgecolor'], alpha=gdf['alpha'])

        # Add basemap
        try:
            ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)
        except Exception as e:
            print(f"Warning: failed to add basemap: {e}")

        ax.axis('off')

        temp_png = os.path.join(tempfile.gettempdir(), f'globle_map_{int(time.time()*1000)}.png')
        fig.savefig(temp_png, bbox_inches='tight', dpi=150)
        plt.close(fig)
        return temp_png
