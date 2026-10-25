class ValueNoise:
    def __init__(self, seed: int):
        self.seed = seed
        self._cache = {}

    def _rand(self, ix: int, iy: int) -> float:
        key = (ix, iy)
        if key in self._cache:
            return self._cache[key]

        # Быстрый целочисленный хэш (в стиле Wang / PCG)
        h = (self.seed * 0x9E3779B1) ^ (ix * 0x85EBCA77) ^ (iy * 0xC2B2AE3D)
        h = (h ^ (h >> 16)) * 0x85EBCA6B & 0xFFFFFFFF
        h = (h ^ (h >> 13)) * 0xC2B2AE35 & 0xFFFFFFFF
        h = h ^ (h >> 16)

        value = h / 0xFFFFFFFF  # нормализуем в [0, 1]
        self._cache[key] = value
        return value

    @staticmethod
    def _smooth(t: float) -> float:
        return t * t * (3 - 2 * t)

    def sample(self, x: float, y: float) -> float:
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + 1, y0 + 1
        fx, fy = x - x0, y - y0
        sx, sy = self._smooth(fx), self._smooth(fy)

        v00 = self._rand(x0, y0)
        v10 = self._rand(x1, y0)
        v01 = self._rand(x0, y1)
        v11 = self._rand(x1, y1)

        top = v00 + (v10 - v00) * sx
        bot = v01 + (v11 - v01) * sx
        return top + (bot - top) * sy

    def fbm(self, x: float, y: float, octaves: int = 4) -> float:
        total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            total += self.sample(x * freq, y * freq) * amp
            norm += amp
            amp *= 0.5
            freq *= 2
        return total / norm
