import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

class MissionPage extends StatelessWidget {
  final double sliderValue;

  const MissionPage(this.sliderValue, {super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    // return MapView();
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'On MISSION',
          style: textstyle,
        ),
        centerTitle: true,
        backgroundColor: theme.colorScheme.primary,
      ),
      body: Stack(
        children:[
          const MapView(),
          Center(
            child: Text(
              'Slider Value from Setup Page: $sliderValue',
              style: const TextStyle(fontSize: 18),
            ),
          ),
        ]
      )
    );
  }
}

class MapView extends StatefulWidget {
  const MapView({super.key});

  @override
  _MapViewState createState() => _MapViewState();
}

class _MapViewState extends State<MapView> {
  // マップビューの初期位置
  final CameraPosition _initialLocation = const CameraPosition(target: LatLng(0.0, 0.0)); // 追加
  // マップの表示制御用
  late GoogleMapController mapController;

  @override
  Widget build(BuildContext context) {
    // 画面の幅と高さを決定する
    var height = MediaQuery.of(context).size.height;
    var width = MediaQuery.of(context).size.width;

    return SizedBox(
      height: height,
      width: width,
      child: Scaffold(
        body: Stack(
          children: <Widget>[
            GoogleMap(
              // initialCameraPosition: CameraPosition( //マップの初期位置を指定
              //   zoom: 17,                         //ズーム
              //   target: LatLng(35.0, 135.0),     //経度,緯度
              //   tilt: 45.0,                     //上下の角度
              //   bearing: 90.0
              // ),                //指定した角度だけ回転する
              initialCameraPosition: _initialLocation,
              myLocationEnabled: true,
              myLocationButtonEnabled: false,
              mapType: MapType.normal,
              zoomGesturesEnabled: true,
              zoomControlsEnabled: false,
              onMapCreated: (GoogleMapController controller) {
                mapController = controller;
              },
            ),
          ],
        ),
      ),
    );
  }
}
