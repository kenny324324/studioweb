/**
 * findtoilet 地區頁分群邏輯。
 * 1:1 移植自 scripts/generate-regional-pages.py（以該腳本為準）。
 */
import rawData from "../data/toilets.json";

export interface Toilet {
  /** 名稱 */
  n: string;
  /** 地址 */
  a: string;
  /** 緯度 */
  lt: number;
  /** 經度 */
  lg: number;
  /** 環境部評等 1=特優級 2=優等級 3=普通級 4=不合格 */
  g?: number;
  /** 場所類別 */
  c?: string;
  /** 設施 bitmask */
  f?: number;
  /** 廁間數 */
  tc?: number;
}

export const BASE_URL = "https://kenny324324.github.io/studioweb";

/** 行政區頁面產生門檻：少於此數量不產生獨立頁 */
export const MIN_TOILETS_PER_DISTRICT = 3;

export const GRADE_LABELS: Record<number, string> = {
  1: "特優級",
  2: "優等級",
  3: "普通級",
  4: "不合格",
};

/** 臺 → 台 正規化 */
export function normalizeCity(name: string): string {
  return name.replace(/臺/g, "台");
}

/** 縣市 → slug 對照 */
export const CITY_SLUGS: Record<string, string> = {
  台北市: "taipei", 新北市: "newtaipei", 桃園市: "taoyuan",
  台中市: "taichung", 台南市: "tainan", 高雄市: "kaohsiung",
  基隆市: "keelung", 新竹市: "hsinchu-city", 新竹縣: "hsinchu",
  苗栗縣: "miaoli", 彰化縣: "changhua", 南投縣: "nantou",
  雲林縣: "yunlin", 嘉義市: "chiayi-city", 嘉義縣: "chiayi",
  屏東縣: "pingtung", 宜蘭縣: "yilan", 花蓮縣: "hualien",
  台東縣: "taitung", 澎湖縣: "penghu", 金門縣: "kinmen",
  連江縣: "lienchiang",
};

const SUFFIX_RE = /[鄉鎮市區]$/;
const SUFFIXES = "鄉鎮市區";

/** 區域名稱 → URL slug（去掉鄉鎮市區後綴，例：板橋區 → 板橋） */
export function districtSlug(districtName: string): string {
  return districtName.replace(SUFFIX_RE, "").toLowerCase();
}

/** 從地址提取區域名稱（含全形空格正規化） */
export function extractDistrict(address: string): string | null {
  const m = address.match(/^.{3}(.{2,3}[鄉鎮市區])/);
  if (!m) return null;
  // 「中　區」「北　區」等含全形／半形空格的名稱 → 正規化為「中區」「北區」
  const district = m[1].replace(/　/g, "").replace(/ /g, "");
  if (district.length < 2) return null;
  return district;
}

/**
 * 合併貪婪比對造成的錯誤區名。
 * 例：地址「南港區市民大道…」會被截出「南港區市」；其去尾後為「南港區」，
 * 而「南港區」去尾後的「南港」已是本縣市的正常區名，此時將「南港區市」併回「南港區」。
 */
export function mergeBogusDistricts(
  districts: Map<string, Toilet[]>,
): Map<string, Toilet[]> {
  const bases = new Map<string, string>();
  for (const d of districts.keys()) {
    if (d !== "其他") bases.set(d.replace(SUFFIX_RE, ""), d); // 後者覆蓋前者，同 Python dict comprehension
  }
  const merged = new Map<string, Toilet[]>();
  for (const [d, toilets] of districts) {
    let target = d;
    if (d !== "其他") {
      const base = d.replace(SUFFIX_RE, ""); // 南港區市 → 南港區
      if (base && SUFFIXES.includes(base[base.length - 1])) {
        const inner = base.slice(0, -1); // 南港區 → 南港
        const normal = bases.get(inner);
        if (normal !== undefined && normal !== d) {
          target = normal; // 併回正常區名
        }
      }
    }
    if (!merged.has(target)) merged.set(target, []);
    merged.get(target)!.push(...toilets);
  }
  return merged;
}

/** 將資料依縣市 → 區域分群 */
export function groupData(data: Toilet[]): Map<string, Map<string, Toilet[]>> {
  const cities = new Map<string, Map<string, Toilet[]>>();
  for (const d of data) {
    const addr = d.a ?? "";
    if (addr.length < 3) continue;
    const city = normalizeCity(addr.slice(0, 3));
    if (!(city in CITY_SLUGS)) continue;
    const district = extractDistrict(addr) ?? "其他";
    if (!cities.has(city)) cities.set(city, new Map());
    const districts = cities.get(city)!;
    if (!districts.has(district)) districts.set(district, []);
    districts.get(district)!.push(d);
  }
  const merged = new Map<string, Map<string, Toilet[]>>();
  for (const [city, districts] of cities) {
    merged.set(city, mergeBogusDistricts(districts));
  }
  return merged;
}

/** 回傳會實際產生獨立頁面的行政區（與連結、JSON-LD 共用同一條件） */
export function publishableDistricts(
  districts: Map<string, Toilet[]>,
): Map<string, Toilet[]> {
  const out = new Map<string, Toilet[]>();
  for (const [d, ts] of districts) {
    if (d !== "其他" && ts.length >= MIN_TOILETS_PER_DISTRICT) out.set(d, ts);
  }
  return out;
}

/** 統計各類別廁所數量（依數量遞減，穩定排序） */
export function categoryStats(toilets: Toilet[]): Array<[string, number]> {
  const cats = new Map<string, number>();
  for (const t of toilets) {
    const c = t.c ?? "其他";
    cats.set(c, (cats.get(c) ?? 0) + 1);
  }
  return [...cats.entries()].sort((a, b) => b[1] - a[1]);
}

/** 統計評等分布（依標籤排序） */
export function gradeStats(toilets: Toilet[]): Array<[string, number]> {
  const grades = new Map<string, number>();
  for (const t of toilets) {
    const g = t.g ?? 0;
    const label = GRADE_LABELS[g];
    if (label) grades.set(label, (grades.get(label) ?? 0) + 1);
  }
  return [...grades.entries()].sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
}

/** 計算平均座標（四捨五入到小數 4 位） */
export function avgCoords(toilets: Toilet[]): [number, number] {
  if (!toilets.length) return [23.7, 120.96];
  const lat = toilets.reduce((s, t) => s + t.lt, 0) / toilets.length;
  const lng = toilets.reduce((s, t) => s + t.lg, 0) / toilets.length;
  return [Math.round(lat * 10000) / 10000, Math.round(lng * 10000) / 10000];
}

/** 主要公廁：評等優先（缺評等排最後）、廁間數多者優先，取前 10 */
export function topToilets(toilets: Toilet[], limit = 10): Toilet[] {
  return [...toilets]
    .sort((a, b) => ((a.g ?? 99) - (b.g ?? 99)) || ((b.tc ?? 1) - (a.tc ?? 1)))
    .slice(0, limit);
}

// ---- 快取的分群結果 ----

const allToilets = rawData as Toilet[];
export const citiesData: Map<string, Map<string, Toilet[]>> = groupData(allToilets);

export interface CityEntry {
  city: string;
  slug: string;
  districts: Map<string, Toilet[]>;
  total: number;
}

/** 所有縣市（依資料出現順序） */
export function getCities(): CityEntry[] {
  const out: CityEntry[] = [];
  for (const [city, districts] of citiesData) {
    let total = 0;
    for (const ts of districts.values()) total += ts.length;
    out.push({ city, slug: CITY_SLUGS[city], districts, total });
  }
  return out;
}

/** 全站總數 */
export function grandTotal(): number {
  return getCities().reduce((s, c) => s + c.total, 0);
}
