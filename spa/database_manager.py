import logging
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, func, desc, DateTime
from sqlalchemy.orm import relationship

from model import Model, session, metadata, engine

log = logging.getLogger(__name__)


class Host(Model):
    __tablename__ = 'host'

    id = Column(Integer, primary_key=True)
    name = Column(String(150))


class Map(Model):
    __tablename__ = 'map'

    id = Column(Integer, primary_key=True)
    name = Column(String(150))


class MapSettings(Model):
    __tablename__ = 'map_settings'

    map_id = Column(Integer, ForeignKey(Map.id), primary_key=True)
    host_id = Column(Integer, ForeignKey(Host.id), primary_key=True)
    teams = Column(String(150))
    start_pos_type = Column(String(150))
    boxes = Column(String(150))

    map = relationship(Map)
    host = relationship(Host)


class Preset(Model):
    __tablename__ = 'preset'

    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey(Host.id))
    name = Column(String(150))
    config = Column(String(150))

    host = relationship(Host)


class Smurf(Model):
    __tablename__ = 'smurf'

    id = Column(Integer, primary_key=True)
    spring_id = Column(String(150))
    user_id = Column(String(150))
    country_id = Column(String(150))
    cpu_id = Column(String(150))
    color_hex = Column(String(6))
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)


class SmurfIP(Model):
    __tablename__ = 'smurf_ip'

    id = Column(Integer, primary_key=True)
    smurf_id = Column(ForeignKey(Smurf.id), nullable=False)
    IPID = Column(String(150))
    first_seen = Column(DateTime)
    last_seen = Column(DateTime)

    Smurf = relationship(Smurf)


class KeyValue(Model):
    __tablename__ = 'key_value'

    id = Column(Integer, primary_key=True)
    key = Column(String(150))
    value = Column(String(150))


class DatabaseManager(object):

    def __init__(self):
        self.cache = {}

    def search_user(self, user_name):
        return session.query(
            Smurf.id, KeyValue.value.label('user'), func.max(Smurf.last_seen).label('last_seen'), Smurf.color_hex
        ).outerjoin(
            KeyValue, Smurf.user_id == KeyValue.id
        ).filter(
            KeyValue.value == user_name
        ).group_by(
            Smurf.id
        ).one_or_none()

    def store_boxes(self, host_name, map_name, teams, start_pos_type, boxes):
        host_id = self.get_host_id(host_name)
        map_id = self.get_map_id(map_name)
        map_settings = MapSettings.where(
            map_id=map_id, host_id=host_id
        ).one_or_none()
        if not map_settings:
            map_settings = MapSettings.create(
                map_id=map_id,
                host_id=host_id
            )
        map_settings.teams = teams
        map_settings.start_pos_type = start_pos_type
        map_settings.boxes = boxes
        map_settings.save()
        session.commit()

    def load_boxes(self, host_name, map_name, teams, start_pos_type):
        return MapSettings.where(
            host___name=host_name,
            map___name=map_name,
            teams=teams,
            start_pos_type=start_pos_type
        ).value(MapSettings.boxes)

    def store_preset(self, host_name, preset_name, config):
        host_id = self.get_host_id(host_name)
        preset = Preset.where(
            host_id=host_id,
            name=preset_name
        ).one_or_none()
        if not preset:
            preset = Preset.create(
                host_id=host_id,
                name=preset_name,
                config=config
            )
        preset.config = config
        preset.save()
        session.commit()

    def load_preset(self, host_name, preset_name):
        return Preset.where(
            host___name=host_name,
            name=preset_name
        ).value(Preset.config)

    def store_battle(self, host_spring_id, rank_host_id, game_id, map_name, created_at, game_hash, data):
        map_id = self.get_kv_id('Map', map_name)
        game_id = self.get_kv_id('Game', game_id)
        host_id = self.get_kv_id('SpringID', host_spring_id)
        rank_host_id = self.get_kv_id('RankingGroup', rank_host_id)

        log.info(
            'store_battle called with '
            'host_spring_id=%s, ',
            'rank_host_id=%s, ',
            'game_id=%s, ',
            'map_name=%s, ',
            'created_at=%s, ',
            'game_hash=%s, ',
            'data=%s',
            host_spring_id,
            rank_host_id,
            game_id,
            map_name,
            created_at,
            game_hash,
            data,
        )
        # record = BattleRecord.find(unique_id=unique_id)
        # if not record:
        #     record = BattleRecord()
        # record.update(
        #     host_id=host_id,
        #     rank_host_id=rank_host_id,
        #     game_hash=game_hash,
        #     game_id=game_id,
        #     created_at=created_at,
        #     map_id=map_id,
        #     data=data,
        # )
        # session.commit()

    def update_smurf_color(self, user_id, color):
        smurf = Smurf.find(user_id)
        if not smurf:
            smurf = Smurf.create()
        smurf.color_hex = color
        smurf.save()
        session.commit()

    def store_smurf(self, spring_id, user_id, IP, country, cpu_id):
        spring_id = self.get_kv_id('SpringID', spring_id)
        user_id = self.get_kv_id('User', user_id)
        country_id = self.get_kv_id('Country', country)
        cpu_id = self.get_kv_id('CPU', cpu_id)

        insert = False
        smurf = Smurf.where(
            spring_id=spring_id,
            user_id=user_id,
            country_id=country_id,
            cpu_id=cpu_id
        ).order_by(desc(Smurf.first_seen)).first()

        if smurf:
            max_first_seen = session.query(func.max(Smurf.first_seen)).filter_by(spring_id=spring_id).scalar()
            if max_first_seen == smurf.first_seen:
                smurf.last_seen = datetime.utcnow()
                smurf.save()
            else:
                insert = True
        else:
            insert = True
        if insert:
            smurf = Smurf.create(
                spring_id=spring_id,
                user_id=user_id,
                country_id=country_id,
                cpu_id=cpu_id,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )

        if IP:
            IPID = self.get_kv_id('IP', IP)
            insert = False

            smurfIP = SmurfIP.where(
                smurf_id=smurf.id,
                IPID=IPID
            ).order_by(desc(SmurfIP.first_seen)).first()
            if smurfIP:

                max_first_seen = session.query(func.max(SmurfIP.first_seen)).filter_by(smurf_id=smurf.id).scalar()
                if max_first_seen == smurfIP.first_seen:
                    smurfIP.last_seen = datetime.utcnow()
                    smurfIP.save()
                else:
                    insert = True
            else:
                insert = True

            if insert:
                SmurfIP.create(
                    smurf_id=smurf.id,
                    IPID=IPID,
                    first_seen=datetime.utcnow(),
                    last_seen=datetime.utcnow(),
                )

        session.commit()

    def get_kv_id(self, key, value):
        if key in self.cache:
            if value in self.cache[key]:
                return self.cache[key][value]
        else:
            self.cache[key] = {}
            for key_value in KeyValue.where(key=key).all():
                self.cache[key][key_value.value] = str(key_value.id)
            if value in self.cache[key]:
                return self.cache[key][value]
        if not value:
            return 0

        key_value_id = KeyValue.where(key=key, value=value).value(KeyValue.id)

        if not key_value_id:
            KeyValue.create(
                key=key,
                value=value
            )
            session.commit()
            return self.get_kv_id(key, value)
        self.cache[key][value] = key_value_id
        return key_value_id

    def get_host_id(self, host_name):
        host_id = Host.where(name=host_name).value(Host.id)
        if not host_id:
            host = Host.create(name=host_name)
            session.commit()
            return host.id
        return host_id

    def get_map_id(self, map_name):
        map_id = Map.where(name=map_name).value(Host.id)
        if not map_id:
            map = Map.create(name=map_name)
            session.commit()
            return map.id
        return map_id


# metadata.drop_all(bind=engine)
metadata.create_all(bind=engine)
