import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:geolocator/geolocator.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

const String SERVER_URL = 'https://';

class MissionPage extends HookWidget {
  final double distance;
  const MissionPage({required this.distance, super.key});

  Future<Position> getCurrentLocation() async {
    // 現在の位置を返す
    Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high);
    return position;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.onPrimary,
    );

    final future = useMemoized(getCurrentLocation);
    final snapshot = useFuture(future, initialData: null);

    if (snapshot.hasData && snapshot.data != null) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'On MISSION',
            style: textstyle,
          ),
          centerTitle: true,
          backgroundColor: theme.colorScheme.primary,
        ),
        body: Stack(children: [
          MapView(currentLocation: snapshot.data!),
          Center(
            child: Text(
              'Slider Value from Setup Page: $distance',
              style: const TextStyle(fontSize: 18),
            ),
          ),
          SnapView(),
        ]),
      );
    } else if (snapshot.hasError) {
      return const Center(
        child: Text('error occurred'),
      );
    } else {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            'On MISSION',
            style: textstyle,
          ),
          centerTitle: true,
          backgroundColor: theme.colorScheme.primary,
        ),
        body: const Center(
          child: Column(
            children: [
              Text("NOW LOADING"),
            ],
          ),
        ),
      );
    }
  }
}

class SnapView extends StatelessWidget {
  const SnapView({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      // 初期の表示割合
      initialChildSize: 0.2,
      // 最小の表示割合
      minChildSize: 0.2,
      // 最大の表示割合
      maxChildSize: 0.5,
      // ドラッグを離した時に一番近いsnapSizeになるか
      snap: true,
      // snapで止める時の割合
      snapSizes: const [0.2, 0.5],
      builder: (BuildContext context, ScrollController scrollController) {
        //　表示したいWidgetを返す
        return Container(
          decoration: const BoxDecoration(
            color: Color.fromARGB(255, 218, 243, 255),
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
            ),
          ),
          child: ListView.builder(
              controller: scrollController,
              itemCount: 1,
              itemBuilder: (BuildContext context, int index) {
                return SnapViewState();
              }),
        );
      },
    );
  }
}

class SnapViewState extends StatelessWidget {
  const SnapViewState({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text("menu top"),
        SizedBox(
          height: 1000,
        ),
        Text("menu bottom"),
      ],
    );
  }
}

class MapView extends StatefulWidget {
  final Position currentLocation;
  const MapView({required this.currentLocation, super.key});

  @override
  _MapViewState createState() => _MapViewState();
}

class _MapViewState extends State<MapView> {
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
              initialCameraPosition: CameraPosition(
                //マップの初期位置を指定
                zoom: 17, //ズーム
                target: LatLng(
                  //緯度, 経度
                  widget.currentLocation.latitude,
                  widget.currentLocation.longitude,
                ),
              ),
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
