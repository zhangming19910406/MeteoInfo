from PyQt5.QtCore import *

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pyproj, shapefile, shapely.geometry, sys
import os
import math


class View(QGraphicsView):
    
    projections = {
    'mercator': pyproj.Proj(init="epsg:3395"),
    'spherical': pyproj.Proj('+proj=ortho +lon_0=28 +lat_0=47')
    }
    
    def __init__(self, parent):
        super().__init__()
        self.setCacheMode(self.CacheBackground)
        self.setDragMode(self.ScrollHandDrag)
        self.setResizeAnchor(self.AnchorUnderMouse)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.setTransformationAnchor(self.AnchorUnderMouse)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.setRenderHint(QPainter.Antialiasing)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.ratio = 1/100
        self.offset = (-13000, 3000)
        self.offset = (0, 0)
        self.proj = 'mercator'
        self.scale(.02, .02)
        self.init_map()

    def wheelEvent(self, event):
         if event.modifiers() & Qt.ControlModifier:
            self.scale_view(math.pow(2.0, -event.angleDelta().y()/240.0))
            return event.accept()

    def scale_view(self, scale_factor):
        factor = self.transform().scale(scale_factor, scale_factor).mapRect(QRectF(0, 0, 1, 1)).width()
        if factor < 0.007 or factor > 1:
            return
        self.scale(scale_factor, scale_factor)

    # def mousePressEvent(self, event):
    #     pos = self.mapToScene(event.pos())
    #     lon, lat = self.to_geographical_coordinates(pos.x(), pos.y())

    def to_geographical_coordinates(self, x, y):
        px, py = (x - self.offset[0])/self.ratio, (self.offset[1] - y)/self.ratio
        return self.projections[self.proj](px, py, inverse=True)
        
    def to_canvas_coordinates(self, longitude, latitude):
        px, py = self.projections[self.proj](longitude, latitude)
        return px*self.ratio + self.offset[0], -py*self.ratio + self.offset[1]

    # This is a new init map function, we have a new.
    def init_map_old(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        sf = shapefile.Reader(script_dir + '/data/ne_50m_admin_0_countries.shp')
        polygons = sf.shapes()
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            if polygon.geom_type == 'Polygon':
                polygon = [polygon]
            for land in polygon:
                qt_polygon = QPolygonF()
                for lon, lat in land.exterior.coords:
                    if lat < -80:
                        continue
                    px, py = self.to_canvas_coordinates(lon, lat)
                    if px > 1e+10:
                        continue
                    qt_polygon.append(QPointF(px, py))
                polygon_item = QGraphicsPolygonItem(qt_polygon)
                polygon_item.setBrush(QBrush(QColor(200, 200, 200)))
                polygon_item.setZValue(1)
                polygon_item.setPos(0, 0)
                self.scene.addItem(polygon_item)

    def init_map(self):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        sf = shapefile.Reader(script_dir + '/data/ne_50m_admin_0_countries.shp')
        kinds_of_polygons = sf.shapes()

        sample_polygons = []
        for kinds_of_polygon in kinds_of_polygons:
            kinds_of_polygon = shapely.geometry.shape(kinds_of_polygon)
            _type = kinds_of_polygon.geom_type
            if _type == "Polygon":
                sample_polygons.append(kinds_of_polygon)
            elif _type == "MultiPolygon":
                for polygon in kinds_of_polygon.geoms:
                    sample_polygons.append(polygon)

        for land in sample_polygons:
            qt_polygon = QPolygonF()
            for lon, lat in land.exterior.coords:
                if lat < -80:
                    continue
                px, py = self.to_canvas_coordinates(lon, lat)
                if px > 1e+10:
                    continue
                qt_polygon.append(QPointF(px, py))
            polygon_item = QGraphicsPolygonItem(qt_polygon)
            polygon_item.setBrush(QBrush(QColor(200, 200, 200)))
            polygon_item.setZValue(1)
            self.scene.addItem(polygon_item)

    def draw_polygons(self):
        sf = shapefile.Reader(self.shapefile)
        polygons = sf.shapes() 
        for polygon in polygons:
            polygon = shapely.geometry.shape(polygon)
            if polygon.geom_type == 'Polygon':
                polygon = [polygon]
            for land in polygon:
                qt_polygon = QPolygonF()
                for lon, lat in land.exterior.coords:
                    if lat < -80:
                        continue
                    px, py = self.to_canvas_coordinates(lon, lat)
                    if px > 1e+10:
                        continue
                    qt_polygon.append(QPointF(px, py))
                polygon_item = QGraphicsPolygonItem(qt_polygon)
                polygon_item.setBrush(QBrush(QColor(100, 200, 200)))
                polygon_item.setZValue(1)
                yield polygon_item
                
    def draw_water(self):
        if self.proj in ('spherical'):
            cx, cy = self.to_canvas_coordinates(28, 47)
            R = 6371000*self.ratio
            # draw an ellipse (x, y, width, height)
            earth_water = QGraphicsEllipseItem(cx - R, cy - R, 2*R, 2*R)
            earth_water.setZValue(0)
            earth_water.setBrush(QBrush(QColor(64, 164, 223)))
            self.polygons.addToGroup(earth_water)

    def redraw_map(self):
        if hasattr(self, 'polygons'):
            self.scene.removeItem(self.polygons)
        self.polygons = self.scene.createItemGroup(self.draw_polygons())
        self.draw_water()


class PyQTGISS(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('MeteInfo')
        self.setWindowIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + os.path.sep + '/icon/ship_small.ico'))
        self.view = View(self)
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)
        layout.addWidget(self.view, 0, 0)

        self.tool_bar()
        self.status_bar()
        self.menu_bar()


    def menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = QMenu('文件', self)
        menu_bar.addMenu(file_menu)
        import_shapefile = QAction('导入数据', self)
        import_shapefile.triggered.connect(self.import_shapefile)
        file_menu.addAction(import_shapefile)

        edit_menu = QMenu('编辑', self)
        menu_bar.addMenu(edit_menu)

        option_menu = QMenu('选项', self)
        menu_bar.addMenu(option_menu)

        view_menu = QMenu('视图', self)
        menu_bar.addMenu(view_menu)
        switch_projection = QAction('转换投影', self)
        switch_projection.triggered.connect(self.switch_projection)
        view_menu.addAction(switch_projection)

        tool_menu = QMenu('工具', self)
        menu_bar.addMenu(tool_menu)

        help_menu = QMenu('帮助', self)
        menu_bar.addMenu(help_menu)

    def status_bar(self):
        # lon = self.view().lon
        # lat = self.view().lat
        # self.statusBar.showMessage(lon)
        pass

    def tool_bar(self):
        self.toolbar = self.addToolBar('文件')
        script_dir = os.path.dirname(os.path.realpath(__file__))
        open_act = QAction(QIcon(script_dir + os.path.sep + '/icon/open.ico'), '打开', self)
        open_act.triggered.connect(self.import_shapefile)
        open_act.setShortcut('Ctrl+O')
        self.toolbar.addAction(open_act)

        save_act = QAction(QIcon(script_dir + os.path.sep + '/icon/save.ico'), '保存', self)
        self.toolbar.addAction(save_act)

        forward_act = QAction(QIcon(script_dir + os.path.sep + '/icon/arrow_left.ico'),
                              '后退',
                              self
                              )
        self.toolbar.addAction(forward_act)

        back_act = QAction(QIcon(script_dir + os.path.sep + '/icon/arrow_right.ico'),
                           '前进',
                           self
                           )
        self.toolbar.addAction(back_act)

        parent_act = QAction(QIcon(script_dir + os.path.sep + '/icon/arrow_up.ico'), '上一级', self)
        self.toolbar.addAction(parent_act)

        son_act = QAction(QIcon(script_dir + os.path.sep + '/icon/arrow_down.ico'), '下一级', self)
        self.toolbar.addAction(son_act)

        about_act = QAction(QIcon(script_dir + os.path.sep + '/icon/about.ico'), '关于', self)
        self.toolbar.addAction(about_act)

        exit_act = QAction(QIcon(script_dir + os.path.sep + '/icon/exit.ico'), '退出', self)
        exit_act.triggered.connect(qApp.quit)
        exit_act.setShortcut('Ctrl+Q')
        self.toolbar.addAction(exit_act)

    def import_shapefile(self):
        self.view.shapefile = QFileDialog.getOpenFileName(self, 'Import')[0]
        self.view.redraw_map()
        
    def switch_projection(self):
        # self.view.proj = 'mercator' if self.view.proj == 'spherical' else 'spherical'
        self.view.proj = 'spherical' if self.view.proj == 'mercator' else 'mercator'
        self.view.redraw_map()

    def center(self):
        # center the window on the screen
        screen = QDesktopWidget().screenGeometry()
        size = self.geometry()
        moveH = screen.width() - size.width()
        moveV = screen.height() - size.height()
        self.move(int(moveH/2), int(moveV/2))


if str.__eq__(__name__, '__main__'):
    app = QApplication(sys.argv)
    window = PyQTGISS()
    window.setGeometry(100, 100, 1500, 900)
    window.center()
    window.show()
    sys.exit(app.exec_())
'''
pyinstaller  -w -i ./icon/ship_medium.ico --key=1234567890123456 ./MeteoInfo.py
pyinstaller  -w -i ./icon/ship_medium.ico ./MeteoInfo.py
'''
