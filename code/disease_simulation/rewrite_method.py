


def get_ring_neighborhood(
    self,
    pos,
    include_center: bool = False,
    radius: int = 1,
):
    def switch_coordinate(coord,coordinates):
        if self.out_of_bounds(coord):
                    # Skip if not a torus and new coords out of bounds.
            if not self.torus:
                return
            coord = self.torus_adj(coord)
        coordinates.add(coord)


    moore = False
    cache_key = (pos, moore, include_center, radius)
    neighborhood = self._neighborhood_cache.get(cache_key, None)

    if neighborhood is None:
        coordinates  = set()

        x, y = pos
        for dx in range(radius+1):
            for dy in range(radius+1-dx):
                if dx == 0 and dy == 0 and not include_center:
                    continue
                # Skip coordinates that are outside manhattan distance
                switch_coordinate((x + dx, y + dy),coordinates)
                switch_coordinate((x + dx, y - dy),coordinates)
                switch_coordinate((x - dx, y + dy),coordinates)
                switch_coordinate((x - dx, y - dy),coordinates)


        neighborhood = sorted(coordinates)
        self._neighborhood_cache[cache_key] = neighborhood

    return neighborhood
model_methods = [get_ring_neighborhood]