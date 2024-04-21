import re
import typing as t

from cached_property import cached_property
from pydantic import BaseModel

from source.device.alas.config_utils import *
from source.map.extractor.convert import MapConverter

from source.en_tools.poi_json_api import zh2en


class PointItemModel(BaseModel):
    count: int
    itemId: int


class PointInfoModel(BaseModel):
    content: str
    hiddenFlag: int
    id: int
    itemList: t.List[PointItemModel]
    markerCreatorId: int
    markerTitle: str
    picture: str = ''
    pictureCreatorId: int = 0
    position: str
    refreshTime: int
    version: int
    videoPath: str

    class Config:
        keep_untouched = (cached_property,)


    @cached_property
    def position_tuple(self) -> t.Tuple[float, float]:
        x, y = self.position.split(',')
        x = float(x)
        y = float(y)
        return x, y



class ItemModel(BaseModel):
    areaId: int
    count: int
    defaultContent: str
    defaultCount: int
    defaultRefreshTime: int
    hiddenFlag: int
    iconStyleType: int
    iconTag: str
    id: int
    name: str
    sortIndex: int
    # specialFlag: int
    typeIdList: t.List[int]
    version: int



class AreaModel(BaseModel):
    areaId: int
    code: str
    hiddenFlag: int
    iconTag: str
    isFinal: bool
    name: str
    parentId: int
    sortIndex: int
    version: int


class TeleporterModel(BaseModel):
    id: int
    region: str
    tp: str
    item_id: int
    name: str
    position: t.Tuple[float, float]


class PoiJsonApi:
    def __init__(self, path='./assets/POI_JSON_API/zh_CN/dataset'):
        """
        Args:
            path (str): Path to POI_JSON_API/zh_CN/dataset
        """
        self.path = path

    @classmethod
    def read_json(cls, data, model, attr: str):
        out = {}
        if isinstance(data, str):
            data = read_file(data)

        for row in data:
            row = model(**row)
            key = row.__getattribute__(attr)
            out[key] = row
        return out

    @cached_property
    def data(self) -> t.Dict[int, PointInfoModel]:
        data = {}
        for file in iter_folder(self.path, ext='.json'):
            if not re.search(r'\d+\.json$', file):
                continue
            data.update(self.read_json(file, PointInfoModel, 'id'))
        return data

    @cached_property
    def item(self) -> t.Dict[int, ItemModel]:
        return self.read_json(os.path.join(self.path, './item.json'), ItemModel, 'id')

    @cached_property
    def area(self) -> t.Dict[int, AreaModel]:
        return self.read_json(os.path.join(self.path, './area.json'), AreaModel, 'areaId')

    def findTP(self,itemList) -> int:
        TPname=["秘境","神像","副本","传送锚点"]
        for it in itemList:
            itemId=it.itemId
            if self.item[itemId].iconTag in TPname:
                return itemId
        return None
    
    def teleporter(self,name) -> t.Optional[str]:
        if name == '传送锚点':
            return MapConverter.TP_Teleporter
        if '神像' in name:
            return MapConverter.TP_Statue
        if name == '副本':
            return MapConverter.TP_Instance
        if name == '秘境':
            return MapConverter.TP_Domain
        return None

    def teleporter_name(self,markerTitle,item_id,content) -> str:
        if markerTitle == '传送锚点' or '神像' in markerTitle:
            if item_id == 758:
                return '三界路飨祭'
            res = re.search(r'【(.*)】', content)
            if res:
                name = res.group(1)
                for region in ['蒙德', '璃月', '稻妻', '须弥','枫丹', '层岩巨渊', '金苹果群岛']:
                    if region in name:
                        try:
                            _, name = name.rsplit(' ', maxsplit=1)
                        except ValueError:
                            pass
                return name

            return ''
        else:
            return markerTitle
        
    DICT_AREA_ID = {
        1: MapConverter.REGION_Liyue,
        2: MapConverter.REGION_Liyue,
        3: MapConverter.REGION_Liyue,
        4: MapConverter.REGION_TheChasm,
        5: MapConverter.REGION_Mondstadt,
        6: MapConverter.REGION_Mondstadt,
        8: MapConverter.REGION_GoldenAppleArchipelago,
        10: MapConverter.REGION_GoldenAppleArchipelago,
        11: MapConverter.REGION_Inazuma,
        12: MapConverter.REGION_Inazuma,
        13: MapConverter.REGION_Inazuma,
        14: MapConverter.REGION_Inazuma,
        15: MapConverter.REGION_Enkanomiya,
        16: MapConverter.REGION_ThreeRealmsGatewayOffering,
        17: MapConverter.REGION_Mondstadt,
        18: MapConverter.REGION_Sumeru,
        19: MapConverter.REGION_Sumeru,
        21: MapConverter.REGION_Sumeru,
        22: MapConverter.REGION_Sumeru,
        23: MapConverter.REGION_Sumeru,
        26: MapConverter.REGION_VeluriyamMirage,
        28: MapConverter.REGION_Fontaine,
        29: MapConverter.REGION_Fontaine,
        30: MapConverter.REGION_Fontaine,
        34: MapConverter.REGION_Liyue,
    }

    def iter_teleporter(self, lang='zh_CN'):
        for id_, row in self.data.items():
            item_id=self.findTP(row.itemList)
            if item_id is None :
                continue
            area_id = self.item[item_id].areaId
            region = self.DICT_AREA_ID.get(area_id, area_id)
            layer = MapConverter.convert_REGION_to_LAYER(region)
            position = MapConverter.convert_kongying_to_GIMAP(row.position_tuple, layer=layer).round(3)
            name = self.teleporter_name(row.markerTitle,item_id,row.content)
            if lang=='en_US':
                name = zh2en(name)
            
            tp = TeleporterModel(
                id=row.id,
                region=region,
                tp=self.teleporter(self.item[item_id].iconTag),
                item_id=item_id,
                name=name,
                position=tuple(position),
            )
            yield tp

    def save_teleporter(self,lang='zh_CN'):
        from source.device.alas.map_grids import SelectedGrids
        tp = SelectedGrids(list(self.iter_teleporter(lang=lang)))
        tp = tp.sort('region', 'item_id', 'name', 'id')

        from source.device.alas.code_generator import CodeGenerator
        gen = CodeGenerator()
        gen.Import("""
        from source.map.extractor.reader import TeleporterModel
        """)
        with gen.Dict('DICT_TELEPORTER'):
            for row in tp:
                gen.DictItem(row.id, row)
        gen.write(f'./source/map/data/teleporter_{lang}.py')


if __name__ == '__main__':
    lang='en_US'
    # lang='zh_CN'
    self = PoiJsonApi()
    self.save_teleporter(lang=lang)
