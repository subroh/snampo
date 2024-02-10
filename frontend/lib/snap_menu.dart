// mission_pageで表示するsnapのメニュー
import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:snampo/result_page.dart';

class SnapView extends StatelessWidget {
  const SnapView({
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return DraggableScrollableSheet(
      // 初期の表示割合
      initialChildSize: 0.15,
      // 最小の表示割合
      minChildSize: 0.15,
      // 最大の表示割合
      maxChildSize: 0.6,
      // ドラッグを離した時に一番近いsnapSizeになるか
      snap: true,
      // snapで止める時の割合
      snapSizes: const [0.15, 0.6],
      builder: (BuildContext context, ScrollController scrollController) {
        return Container(
          color: theme.colorScheme.background,
          child: Stack(
            children: [
              Container(
                  height: MediaQuery.of(context).size.height * 0.9,
                  width: MediaQuery.of(context).size.width,
                  child: SingleChildScrollView(
                    controller: scrollController,
                    child: Column(
                      children: [
                        const SizedBox(
                          height: 50,
                        ),
                        SnapViewState(),
                      ],
                    ),
                  )),
              IgnorePointer(
                child: Container(
                  color: theme.colorScheme.background,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        margin: const EdgeInsets.only(top: 20, bottom: 20),
                        height: 10,
                        width: 100,
                        decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(10),
                            color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
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
    final theme = Theme.of(context);
    final titelTextstyle = theme.textTheme.displaySmall!.copyWith(
      color: theme.colorScheme.secondary,
    );
    final buttonTextstyle = theme.textTheme.bodyLarge!.copyWith(
      color: theme.colorScheme.onPrimary,
    );
    return Column(
      children: [
        Text(
          "MISSION",
          style: titelTextstyle,
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("- Spot1: "),
            Container(
              child: SetImage(
                pictureName: "images/test1.jpeg",
              ),
              width: 150,
              height: 150,
            ),
          ],
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text("- Spot2: "),
            Container(
              child: SetImage(
                pictureName: "images/test2.jpeg",
              ),
              width: 150,
              height: 150,
            ),
          ],
        ),
        SizedBox(
          height: 20,
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: theme.colorScheme.primary, // ボタンの背景色
            foregroundColor: theme.colorScheme.onPrimary,
            shape: RoundedRectangleBorder(
              // 形を変えるか否か
              borderRadius: BorderRadius.circular(10), // 角の丸み
            ),
          ),
          onPressed: () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (context) => ResultPage()),
            );
          },
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Text('到着', style: buttonTextstyle),
          ),
        ),
      ],
    );
  }
}

class SetImage extends StatelessWidget {
  final String pictureName;
  const SetImage({
    required this.pictureName,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    return FittedBox(
      fit: BoxFit.contain,
      child: Image.asset(pictureName),
    );
  }
}
