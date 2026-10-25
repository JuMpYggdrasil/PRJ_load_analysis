from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:
    import pvlib
except ImportError as exc:
    pvlib = None
    _PVLIB_IMPORT_ERROR = exc
else:
    _PVLIB_IMPORT_ERROR = None


NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
NASA_PARAMETERS = (
    "ALLSKY_SFC_SW_DWN",
    "ALLSKY_SFC_SW_DNI",
    "ALLSKY_SFC_SW_DIFF",
    "T2M",
    "WS2M",
)
NASA_COLUMN_MAP = {
    "ALLSKY_SFC_SW_DWN": "ghi",
    "ALLSKY_SFC_SW_DNI": "dni",
    "ALLSKY_SFC_SW_DIFF": "dhi",
    "T2M": "temp_air",
    "WS2M": "wind_speed",
}

DEFAULT_TIMEZONE = "Asia/Bangkok"
DEFAULT_TILT = 15.0
DEFAULT_AZIMUTH = 180.0
DEFAULT_REFERENCE_YIELD = 1402.8119
DEFAULT_CACHE_DIR = "solar_cache"
SOLAR_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M"


def _require_pvlib():
    if pvlib is None:
        raise ImportError(
            "pvlib is required for the solar fallback. "
            "Install it with: pip install pvlib==0.10.2"
        ) from _PVLIB_IMPORT_ERROR


def _coord_tag(value):
    return f"{value:.4f}".replace("-", "m").replace(".", "p")


def _profile_path(year, tracking=False):
    suffix = "_tracking" if tracking else ""
    return Path(f"solar_1kW_{year}{suffix}.csv")


def _cache_path(
    year,
    source,
    lat,
    lon,
    cache_dir,
    tracking=False,
    tilt=DEFAULT_TILT,
    azimuth=DEFAULT_AZIMUTH,
    normalize=True,
    target_yield=DEFAULT_REFERENCE_YIELD,
):
    suffix = "_tracking" if tracking else ""
    yield_tag = _coord_tag(target_yield) if normalize else "raw"
    name = (
        f"solar_1kW_{year}_{source}_{_coord_tag(lat)}_{_coord_tag(lon)}"
        f"_t{_coord_tag(tilt)}_a{_coord_tag(azimuth)}_y{yield_tag}"
        f"{suffix}.csv"
    )
    return Path(cache_dir) / name


def _read_profile(path):
    df = pd.read_csv(
        path,
        parse_dates=["timestamp"],
        date_format=SOLAR_TIMESTAMP_FORMAT,
    )
    if "timestamp" not in df.columns or "pv" not in df.columns:
        raise ValueError(f"{path} must contain timestamp and pv columns")
    df["pv"] = pd.to_numeric(df["pv"], errors="coerce")
    df = df.dropna(subset=["timestamp", "pv"]).sort_values("timestamp")
    if df.empty:
        raise ValueError(f"{path} contains no valid rows")
    df = df.set_index("timestamp")
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df[["pv"]]


def _write_profile(pv, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = pv.rename("pv").rename_axis("timestamp").reset_index()
    out["timestamp"] = pd.to_datetime(out["timestamp"]).dt.strftime(
        SOLAR_TIMESTAMP_FORMAT
    )
    out.to_csv(path, index=False)


def _normalize_yield(pv, target_yield):
    pv = pd.Series(pv, dtype=float)
    annual_yield = float(pv.sum())
    if not np.isfinite(annual_yield) or annual_yield <= 0:
        raise ValueError("Generated PV profile has no annual energy")
    return pv * (target_yield / annual_yield)


def _log_profile(source, pv):
    print(
        f"[solar_profile] {source}: rows={len(pv)}, "
        f"annual={pv.sum():,.1f} kWh/kWp, peak={pv.max():,.4f} kW/kWp"
    )


def fetch_nasa_power(
    year,
    lat,
    lon,
    timezone=DEFAULT_TIMEZONE,
    timeout=60,
):
    first_day = max(pd.Timestamp(year=year - 1, month=12, day=31), pd.Timestamp("2001-01-01"))
    last_day = pd.Timestamp(year=year, month=12, day=31)
    params = {
        "parameters": ",".join(NASA_PARAMETERS),
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": first_day.strftime("%Y%m%d"),
        "end": last_day.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC",
    }
    response = requests.get(NASA_POWER_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    parameter = payload.get("properties", {}).get("parameter")
    if not parameter:
        raise RuntimeError("NASA POWER response has no parameter data")

    fill_value = payload.get("header", {}).get("fill_value", -999.0)
    df = pd.DataFrame(parameter)
    missing = [name for name in NASA_PARAMETERS if name not in df.columns]
    if missing:
        raise RuntimeError(f"NASA POWER response missing parameters: {missing}")

    df = df.rename(columns=NASA_COLUMN_MAP)
    df.index = pd.to_datetime(df.index, format="%Y%m%d%H", utc=True)
    df.index = df.index.tz_convert(timezone).tz_localize(None)
    df = df[["ghi", "dni", "dhi", "temp_air", "wind_speed"]].apply(
        pd.to_numeric, errors="coerce"
    )
    df = df.replace(float(fill_value), np.nan)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    expected_index = pd.date_range(
        start=f"{year}-01-01 00:00",
        end=f"{year}-12-31 23:00",
        freq="h",
    )
    df = df.reindex(expected_index)
    if df["ghi"].notna().mean() < 0.95:
        raise RuntimeError(
            f"NASA POWER data coverage for {year} is incomplete "
            f"({df['ghi'].notna().mean():.1%})"
        )

    for column in ("ghi", "dni", "dhi"):
        df[column] = df[column].clip(lower=0).fillna(0.0)
    df["temp_air"] = (
        df["temp_air"].interpolate(limit_direction="both").ffill().bfill().fillna(25.0)
    )
    df["wind_speed"] = (
        df["wind_speed"].interpolate(limit_direction="both").ffill().bfill().fillna(1.0)
    )
    df.index.name = "timestamp"
    return df


def build_pv_profile(
    weather,
    lat,
    lon,
    tilt=DEFAULT_TILT,
    azimuth=DEFAULT_AZIMUTH,
    timezone=DEFAULT_TIMEZONE,
):
    _require_pvlib()
    index = pd.DatetimeIndex(weather.index)
    if index.tz is None:
        index_local = index.tz_localize(timezone)
    else:
        index_local = index.tz_convert(timezone)

    location = pvlib.location.Location(lat, lon, tz=timezone)
    solar_position = location.get_solarposition(index_local)
    dni_extra = pvlib.irradiance.get_extra_radiation(index_local)
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        solar_zenith=solar_position["apparent_zenith"].to_numpy(),
        solar_azimuth=solar_position["azimuth"].to_numpy(),
        dni=weather["dni"].to_numpy(),
        ghi=weather["ghi"].to_numpy(),
        dhi=weather["dhi"].to_numpy(),
        dni_extra=dni_extra.to_numpy(),
        albedo=0.2,
        model="haydavies",
    )
    poa_global = pd.Series(
        np.asarray(poa["poa_global"], dtype=float),
        index=index,
    ).clip(lower=0).fillna(0.0)
    temp_cell = pvlib.temperature.sapm_cell(
        poa_global=poa_global,
        temp_air=weather["temp_air"].to_numpy(),
        wind_speed=weather["wind_speed"].to_numpy(),
        a=-3.56,
        b=-0.075,
        deltaT=3.0,
    )
    dc = pvlib.pvsystem.pvwatts_dc(
        g_poa_effective=poa_global,
        temp_cell=temp_cell,
        pdc0=1000.0,
        gamma_pdc=-0.004,
    )
    ac = pvlib.inverter.pvwatts(dc, pdc0=1000.0, eta_inv_nom=0.96)
    pv_kw = pd.Series(ac, index=index, name="pv").fillna(0.0).clip(lower=0.0) / 1000.0
    return pv_kw


def build_clearsky_profile(
    year,
    lat,
    lon,
    tilt=DEFAULT_TILT,
    azimuth=DEFAULT_AZIMUTH,
    timezone=DEFAULT_TIMEZONE,
):
    _require_pvlib()
    index = pd.date_range(
        start=f"{year}-01-01 00:00",
        end=f"{year}-12-31 23:00",
        freq="h",
    )
    location = pvlib.location.Location(lat, lon, tz=timezone)
    clear = location.get_clearsky(index.tz_localize(timezone), model="ineichen")
    weather = pd.DataFrame(
        {
            "ghi": clear["ghi"].to_numpy(),
            "dni": clear["dni"].to_numpy(),
            "dhi": clear["dhi"].to_numpy(),
            "temp_air": 30.0,
            "wind_speed": 1.0,
        },
        index=index,
    )
    weather.index.name = "timestamp"
    return build_pv_profile(
        weather,
        lat,
        lon,
        tilt=tilt,
        azimuth=azimuth,
        timezone=timezone,
    )


def get_solar_profile(
    year,
    lat,
    lon,
    tilt=DEFAULT_TILT,
    azimuth=DEFAULT_AZIMUTH,
    tracking=False,
    force_fallback=False,
    force_refresh=False,
    normalize=True,
    target_yield=DEFAULT_REFERENCE_YIELD,
    timezone=DEFAULT_TIMEZONE,
    cache_dir=DEFAULT_CACHE_DIR,
    allow_nasa=True,
    allow_clearsky=True,
):
    profile_path = _profile_path(year, tracking=tracking)
    if profile_path.exists() and not force_fallback:
        df = _read_profile(profile_path)
        df.attrs["source"] = "file"
        print(f"[solar_profile] Using existing file: {profile_path}")
        _log_profile("file", df["pv"])
        return df

    if tracking:
        raise NotImplementedError(
            "Fixed-tilt fallback is available only. "
            f"Provide {profile_path} for tracking profiles."
        )

    nasa_cache = _cache_path(
        year,
        "nasa",
        lat,
        lon,
        cache_dir,
        tilt=tilt,
        azimuth=azimuth,
        normalize=normalize,
        target_yield=target_yield,
    )
    clearsky_cache = _cache_path(
        year,
        "clearsky",
        lat,
        lon,
        cache_dir,
        tilt=tilt,
        azimuth=azimuth,
        normalize=normalize,
        target_yield=target_yield,
    )

    if allow_nasa and not force_refresh and nasa_cache.exists():
        df = _read_profile(nasa_cache)
        df.attrs["source"] = "nasa_cache"
        print(f"[solar_profile] Using NASA cache: {nasa_cache}")
        _log_profile("nasa_cache", df["pv"])
        return df

    if allow_nasa:
        try:
            weather = fetch_nasa_power(
                year,
                lat,
                lon,
                timezone=timezone,
            )
            pv = build_pv_profile(
                weather,
                lat,
                lon,
                tilt=tilt,
                azimuth=azimuth,
                timezone=timezone,
            )
            if normalize:
                pv = _normalize_yield(pv, target_yield)
            _write_profile(pv, nasa_cache)
            df = pv.to_frame("pv")
            df.attrs["source"] = "nasa"
            _log_profile("nasa", pv)
            return df
        except Exception as exc:
            print(f"[solar_profile] NASA POWER unavailable: {exc}")

    if allow_clearsky and not force_refresh and clearsky_cache.exists():
        df = _read_profile(clearsky_cache)
        df.attrs["source"] = "clearsky_cache"
        print(f"[solar_profile] Using clear-sky cache: {clearsky_cache}")
        _log_profile("clearsky_cache", df["pv"])
        return df

    if allow_clearsky:
        try:
            pv = build_clearsky_profile(
                year,
                lat,
                lon,
                tilt=tilt,
                azimuth=azimuth,
                timezone=timezone,
            )
            if normalize:
                pv = _normalize_yield(pv, target_yield)
            _write_profile(pv, clearsky_cache)
            df = pv.to_frame("pv")
            df.attrs["source"] = "clearsky"
            _log_profile("clearsky", pv)
            return df
        except Exception as exc:
            raise RuntimeError(
                f"Unable to build a solar profile for {year}: {exc}"
            ) from exc

    raise RuntimeError(f"Unable to build a solar profile for {year}")
